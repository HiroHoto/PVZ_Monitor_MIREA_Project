"""
Модуль: db
Назначение: Управление подключением к базе данных и валидация операций
Зависимости: from config import DB_PATH, DATA_DIR
Экспортирует: get_db(), init_db(), validate_operations()
Безопасность: Доступ к файлам базы данных; содержит логику валидации для целостности данных
"""

import sqlite3
import json
import os
from datetime import datetime
from config import DB_PATH, DATA_DIR

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS pvz (
            pvz_id           INTEGER PRIMARY KEY,
            address          TEXT    NOT NULL,
            capacity_per_hour INTEGER NOT NULL CHECK(capacity_per_hour > 0),
            region           TEXT    NOT NULL DEFAULT 'Нет региона'
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            pvz_id   INTEGER NOT NULL REFERENCES pvz(pvz_id),
            weekday  INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
            open_time  TEXT NOT NULL,
            close_time TEXT NOT NULL,
            CHECK(open_time < close_time)
        );
        CREATE TABLE IF NOT EXISTS operations (
            op_id        INTEGER PRIMARY KEY,
            pvz_id       INTEGER NOT NULL REFERENCES pvz(pvz_id),
            ts           TEXT    NOT NULL,
            type         TEXT    NOT NULL CHECK(type IN ('in','out','return')),
            product_name TEXT    NOT NULL DEFAULT 'Не указан',
            weight_kg    REAL    NOT NULL DEFAULT 0.0 CHECK(weight_kg >= 0)
        );
        CREATE TABLE IF NOT EXISTS error_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            pvz_id    INTEGER,
            ts        TEXT,
            op_type   TEXT,
            reason    TEXT,
            logged_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Seed data if empty
    if cur.execute("SELECT COUNT(*) FROM pvz").fetchone()[0] == 0:
        with open(os.path.join(DATA_DIR, "pvz.json"), encoding='utf-8') as f:
            pvz_data = json.load(f)
        cur.executemany(
            "INSERT OR IGNORE INTO pvz(pvz_id,address,capacity_per_hour,region) VALUES(:pvz_id,:address,:capacity_per_hour,:region)",
            pvz_data
        )

    if cur.execute("SELECT COUNT(*) FROM schedule").fetchone()[0] == 0:
        with open(os.path.join(DATA_DIR, "schedule.json"), encoding='utf-8') as f:
            sched_data = json.load(f)
        cur.executemany(
            "INSERT INTO schedule(pvz_id,weekday,open_time,close_time) VALUES(:pvz_id,:weekday,:open_time,:close_time)",
            sched_data
        )

    if cur.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0:
        with open(os.path.join(DATA_DIR, "operations.json"), encoding='utf-8') as f:
            ops_data = json.load(f)
        # Validate before inserting
        valid_ops, errors = validate_operations(ops_data, conn)
        cur.executemany(
            "INSERT OR IGNORE INTO operations(op_id,pvz_id,ts,type,product_name,weight_kg) VALUES(:op_id,:pvz_id,:ts,:type,:product_name,:weight_kg)",
            valid_ops
        )
        if errors:
            cur.executemany(
                "INSERT INTO error_log(pvz_id,ts,op_type,reason) VALUES(:pvz_id,:ts,:op_type,:reason)",
                errors
            )

    conn.commit()
    conn.close()
    print(f"DB ready at {DB_PATH}")

def migrate_db():
    """Добавляет колонки product_name и weight_kg, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(operations)").fetchall()]
    if "product_name" not in cols:
        cur.execute("ALTER TABLE operations ADD COLUMN product_name TEXT NOT NULL DEFAULT 'Не указан'")
    if "weight_kg" not in cols:
        cur.execute("ALTER TABLE operations ADD COLUMN weight_kg REAL NOT NULL DEFAULT 0.0")
    conn.commit()
    conn.close()
    print("Migration check: product_name, weight_kg — OK")

def validate_operations(ops_data, conn):
    """Run all 5 validations on operations batch."""
    cur = conn.cursor()
    pvz_ids = {r[0] for r in cur.execute("SELECT pvz_id FROM pvz").fetchall()}
    # Build schedule lookup: (pvz_id, weekday) -> (open_h, close_h)
    sched = {}
    for row in cur.execute("SELECT pvz_id, weekday, open_time, close_time FROM schedule").fetchall():
        oh = int(row[2].split(":")[0])
        ch = int(row[3].split(":")[0])
        sched[(row[0], row[1])] = (oh, ch)

    valid, errors = [], []
    for op in ops_data:
        pvz_id = op["pvz_id"]
        ts_str  = op["ts"]
        op_type = op["type"]
        product_name = op.get("product_name", "Не указан")
        weight_kg = op.get("weight_kg", 0.0)
        reason  = None

        # V1: pvz_id must exist
        if pvz_id not in pvz_ids:
            reason = f"Неизвестный pvz_id={pvz_id}"
        # V2: type must be valid
        elif op_type not in ("in", "out", "return"):
            reason = f"Неизвестный тип операции: {op_type}"
        else:
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                reason = f"Неверный формат ts: {ts_str}"
            else:
                weekday = ts.weekday()
                # V3: PVZ must have schedule for this weekday
                if (pvz_id, weekday) not in sched:
                    reason = f"ПВЗ {pvz_id} не работает в день {weekday} ({ts_str})"
                else:
                    oh, ch = sched[(pvz_id, weekday)]
                    op_hour = ts.hour
                    # V4: operation must be within working hours
                    if not (oh <= op_hour < ch):
                        reason = f"Операция вне часов работы ({ts_str}, ПВЗ {pvz_id}, рабочие часы {oh}-{ch})"

        # Валидация product_name
        if not isinstance(product_name, str) or len(product_name) == 0:
            product_name = "Не указан"
        elif len(product_name) > 200:
            reason = f"product_name слишком длинный ({len(product_name)} симв.)"

        # Валидация weight_kg
        if reason is None and (not isinstance(weight_kg, (int, float)) or weight_kg < 0):
            reason = f"Некорректный weight_kg: {weight_kg}"

        if reason:
            errors.append({"pvz_id": pvz_id, "ts": ts_str, "op_type": op_type, "reason": reason})
        else:
            op.setdefault("product_name", "Не указан")
            op.setdefault("weight_kg", 0.0)
            valid.append(op)

    return valid, errors