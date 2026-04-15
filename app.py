"""
ПВЗ Маркетплейса — Flask Backend
Кейс 9: Пункты выдачи маркетплейса
"""

from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
import sqlite3
import json
import os
import csv
import io
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = "pvz-secret-key-2025"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pvz.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── DEMO USERS (roles) ───────────────────────────────────────────────────────
USERS = {
    "operator1":   {"password": "op1pass",  "role": "operator",   "pvz_id": 1, "name": "Иванов А."},
    "operator2":   {"password": "op2pass",  "role": "operator",   "pvz_id": 2, "name": "Петрова Б."},
    "supervisor1": {"password": "suppass",  "role": "supervisor", "region": "Центральный", "name": "Козлов В."},
    "analyst1":    {"password": "anapass",  "role": "analyst",    "name": "Смирнова Г."},
}

# ─── DB INIT ──────────────────────────────────────────────────────────────────
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
            op_id   INTEGER PRIMARY KEY,
            pvz_id  INTEGER NOT NULL REFERENCES pvz(pvz_id),
            ts      TEXT    NOT NULL,
            type    TEXT    NOT NULL CHECK(type IN ('in','out','return'))
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
        with open(os.path.join(DATA_DIR, "pvz.json")) as f:
            pvz_data = json.load(f)
        cur.executemany(
            "INSERT OR IGNORE INTO pvz(pvz_id,address,capacity_per_hour,region) VALUES(:pvz_id,:address,:capacity_per_hour,:region)",
            pvz_data
        )

    if cur.execute("SELECT COUNT(*) FROM schedule").fetchone()[0] == 0:
        with open(os.path.join(DATA_DIR, "schedule.json")) as f:
            sched_data = json.load(f)
        cur.executemany(
            "INSERT INTO schedule(pvz_id,weekday,open_time,close_time) VALUES(:pvz_id,:weekday,:open_time,:close_time)",
            sched_data
        )

    if cur.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0:
        with open(os.path.join(DATA_DIR, "operations.json")) as f:
            ops_data = json.load(f)
        # Validate before inserting
        valid_ops, errors = validate_operations(ops_data, conn)
        cur.executemany(
            "INSERT OR IGNORE INTO operations(op_id,pvz_id,ts,type) VALUES(:op_id,:pvz_id,:ts,:type)",
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

        if reason:
            errors.append({"pvz_id": pvz_id, "ts": ts_str, "op_type": op_type, "reason": reason})
        else:
            valid.append(op)

    return valid, errors

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Требуется авторизация"}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return jsonify({"error": "Требуется авторизация"}), 401
            user = USERS.get(session["user"])
            if not user or user["role"] not in roles:
                return jsonify({"error": "Недостаточно прав"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    username = session.get("user")
    if not username:
        return None
    u = USERS.get(username, {})
    return {"username": username, **u}

# ─── ROUTES: AUTH ─────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Неверный логин или пароль"}), 401
    session["user"] = username
    return jsonify({
        "ok": True,
        "username": username,
        "role": user["role"],
        "name": user["name"]
    })

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401
    return jsonify(user)

# ─── ROUTES: PVZ LIST ─────────────────────────────────────────────────────────
@app.route("/api/pvz")
@login_required
def get_pvz_list():
    user = get_current_user()
    conn = get_db()
    if user["role"] == "operator":
        rows = conn.execute(
            "SELECT * FROM pvz WHERE pvz_id=?", (user["pvz_id"],)
        ).fetchall()
    elif user["role"] == "supervisor":
        rows = conn.execute(
            "SELECT * FROM pvz WHERE region=?", (user.get("region", ""),)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pvz").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/pvz/<int:pvz_id>")
@login_required
def get_pvz(pvz_id):
    user = get_current_user()
    if user["role"] == "operator" and user["pvz_id"] != pvz_id:
        return jsonify({"error": "Нет доступа"}), 403
    conn = get_db()
    pvz = conn.execute("SELECT * FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    schedule = conn.execute(
        "SELECT * FROM schedule WHERE pvz_id=? ORDER BY weekday", (pvz_id,)
    ).fetchall()
    conn.close()
    if not pvz:
        return jsonify({"error": "ПВЗ не найден"}), 404
    return jsonify({
        "pvz": dict(pvz),
        "schedule": [dict(s) for s in schedule]
    })

# ─── ROUTES: REGIONS ──────────────────────────────────────────────────────────
@app.route("/api/regions")
@login_required
def get_regions():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT region FROM pvz ORDER BY region").fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])

# ─── ROUTES: OPERATIONS (CRUD) ────────────────────────────────────────────────
@app.route("/api/operations", methods=["GET"])
@login_required
def get_operations():
    user = get_current_user()
    conn = get_db()

    conditions = []
    params = []

    if user["role"] == "operator":
        conditions.append("o.pvz_id=?")
        params.append(user["pvz_id"])
    elif user["role"] == "supervisor":
        pvz_ids = [r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()]
        if pvz_ids:
            conditions.append(f"o.pvz_id IN ({','.join('?'*len(pvz_ids))})")
            params.extend(pvz_ids)

    pvz_filter = request.args.get("pvz_id")
    if pvz_filter:
        conditions.append("o.pvz_id=?")
        params.append(int(pvz_filter))

    type_filter = request.args.get("type")
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)

    date_from = request.args.get("date_from")
    date_to   = request.args.get("date_to")
    if date_from:
        conditions.append("DATE(o.ts)>=?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(o.ts)<=?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))

    sql = f"""
        SELECT o.op_id, o.pvz_id, p.address, o.ts, o.type
        FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id
        {where}
        ORDER BY o.ts DESC
        LIMIT ? OFFSET ?
    """
    total_sql = f"SELECT COUNT(*) FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id {where}"
    total = conn.execute(total_sql, params).fetchone()[0]
    rows = conn.execute(sql, params + [limit, offset]).fetchall()
    conn.close()
    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [dict(r) for r in rows]
    })

@app.route("/api/operations", methods=["POST"])
@role_required("operator", "analyst")
def create_operation():
    user = get_current_user()
    data = request.get_json()
    pvz_id  = data.get("pvz_id")
    ts_str  = data.get("ts")
    op_type = data.get("type")

    # Validate inputs
    if not all([pvz_id, ts_str, op_type]):
        return jsonify({"error": "Необходимы pvz_id, ts, type"}), 400
    if op_type not in ("in", "out", "return"):
        return jsonify({"error": "Тип операции должен быть: in, out, return"}), 400

    # Operator can only add to their own pvz
    if user["role"] == "operator" and user["pvz_id"] != pvz_id:
        return jsonify({"error": "Нет доступа к данному ПВЗ"}), 403

    try:
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Формат ts: YYYY-MM-DD HH:MM:SS"}), 400

    conn = get_db()
    pvz = conn.execute("SELECT * FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    if not pvz:
        conn.close()
        return jsonify({"error": f"ПВЗ {pvz_id} не найден"}), 400

    weekday = ts.weekday()
    sched = conn.execute(
        "SELECT open_time, close_time FROM schedule WHERE pvz_id=? AND weekday=?",
        (pvz_id, weekday)
    ).fetchone()

    if not sched:
        reason = f"ПВЗ {pvz_id} не работает в этот день недели ({weekday})"
        conn.execute(
            "INSERT INTO error_log(pvz_id,ts,op_type,reason) VALUES(?,?,?,?)",
            (pvz_id, ts_str, op_type, reason)
        )
        conn.commit()
        conn.close()
        return jsonify({"error": reason}), 400

    oh = int(sched["open_time"].split(":")[0])
    ch = int(sched["close_time"].split(":")[0])
    if not (oh <= ts.hour < ch):
        reason = f"Время {ts_str} вне рабочих часов ПВЗ {pvz_id} ({oh}:00-{ch}:00)"
        conn.execute(
            "INSERT INTO error_log(pvz_id,ts,op_type,reason) VALUES(?,?,?,?)",
            (pvz_id, ts_str, op_type, reason)
        )
        conn.commit()
        conn.close()
        return jsonify({"error": reason}), 400

    cur = conn.execute(
        "INSERT INTO operations(pvz_id,ts,type) VALUES(?,?,?)",
        (pvz_id, ts_str, op_type)
    )
    conn.commit()
    op_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "op_id": op_id}), 201

# ─── ROUTES: REPORT ───────────────────────────────────────────────────────────
@app.route("/api/report/load")
@login_required
def report_load():
    """
    Отчёт «Загрузка ПВЗ» по часам/дням.
    Возвращает: pvz_id, date, hour, ops_per_hour, capacity_per_hour, load, overloaded
    """
    user = get_current_user()
    conn = get_db()

    conditions = ["1=1"]
    params = []

    # Role-based filtering
    if user["role"] == "operator":
        conditions.append("o.pvz_id=?")
        params.append(user["pvz_id"])
    elif user["role"] == "supervisor":
        pvz_ids = [r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()]
        if pvz_ids:
            conditions.append(f"o.pvz_id IN ({','.join('?'*len(pvz_ids))})")
            params.extend(pvz_ids)

    pvz_filter = request.args.get("pvz_id")
    if pvz_filter:
        conditions.append("o.pvz_id=?")
        params.append(int(pvz_filter))

    region_filter = request.args.get("region")
    if region_filter:
        conditions.append("p.region=?")
        params.append(region_filter)

    type_filter = request.args.get("type")
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)

    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")
    conditions.append("DATE(o.ts) BETWEEN ? AND ?")
    params.extend([date_from, date_to])

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            o.pvz_id,
            p.address,
            p.region,
            p.capacity_per_hour,
            DATE(o.ts)              AS date,
            CAST(strftime('%H', o.ts) AS INTEGER) AS hour,
            COUNT(*)                AS ops_per_hour,
            SUM(CASE WHEN o.type='in'     THEN 1 ELSE 0 END) AS ops_in,
            SUM(CASE WHEN o.type='out'    THEN 1 ELSE 0 END) AS ops_out,
            SUM(CASE WHEN o.type='return' THEN 1 ELSE 0 END) AS ops_return
        FROM operations o
        JOIN pvz p ON o.pvz_id = p.pvz_id
        {where}
        GROUP BY o.pvz_id, date, hour
        ORDER BY o.pvz_id, date, hour
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    total_overloaded = 0
    total_intervals = 0

    for r in rows:
        cap = r["capacity_per_hour"]
        ops = r["ops_per_hour"]
        load = round(ops / cap, 4) if cap else 0
        overloaded = load > 1.0
        if overloaded:
            total_overloaded += 1
        total_intervals += 1
        result.append({
            "pvz_id": r["pvz_id"],
            "address": r["address"],
            "region": r["region"],
            "date": r["date"],
            "hour": r["hour"],
            "ops_per_hour": ops,
            "ops_in": r["ops_in"],
            "ops_out": r["ops_out"],
            "ops_return": r["ops_return"],
            "capacity_per_hour": cap,
            "load": load,
            "load_pct": round(load * 100, 1),
            "overloaded": overloaded
        })

    # KPI
    loads = [r["load"] for r in result]
    # Peak hours: 12-14, 18-20
    peak = [r["load"] for r in result if r["hour"] in (12,13,18,19)]
    avg_peak_load = round(sum(peak)/len(peak)*100, 1) if peak else 0
    avg_load = round(sum(loads)/len(loads)*100, 1) if loads else 0
    overload_share = round(total_overloaded/total_intervals*100, 1) if total_intervals else 0

    return jsonify({
        "data": result,
        "kpi": {
            "avg_load_pct": avg_load,
            "avg_peak_load_pct": avg_peak_load,
            "overload_share_pct": overload_share,
            "total_intervals": total_intervals,
            "total_overloaded": total_overloaded
        }
    })

# ─── ROUTES: HEATMAP ──────────────────────────────────────────────────────────
@app.route("/api/report/heatmap")
@login_required
def report_heatmap():
    """Тепловая карта: средняя загрузка по часу × день недели для выбранного ПВЗ."""
    user = get_current_user()
    pvz_id   = request.args.get("pvz_id")
    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")

    if user["role"] == "operator":
        pvz_id = user["pvz_id"]
    elif not pvz_id:
        conn = get_db()
        if user["role"] == "supervisor":
            row = conn.execute("SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)).fetchone()
        else:
            row = conn.execute("SELECT pvz_id FROM pvz").fetchone()
        conn.close()
        pvz_id = row[0] if row else 1

    conn = get_db()
    # role guard
    if user["role"] == "supervisor":
        allowed = {r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()}
        if int(pvz_id) not in allowed:
            conn.close()
            return jsonify({"error": "Нет доступа"}), 403

    rows = conn.execute("""
        SELECT
            CAST(strftime('%w', ts) AS INTEGER) AS dow,
            CAST(strftime('%H', ts) AS INTEGER) AS hour,
            COUNT(*) AS ops
        FROM operations
        WHERE pvz_id=? AND DATE(ts) BETWEEN ? AND ?
        GROUP BY dow, hour
    """, (pvz_id, date_from, date_to)).fetchall()

    cap = conn.execute("SELECT capacity_per_hour FROM pvz WHERE pvz_id=?", (pvz_id,)).fetchone()
    cap = cap[0] if cap else 1
    conn.close()

    # dow: 0=Sun in SQLite strftime('%w'), remap to 0=Mon
    DOW_MAP = {0:6, 1:0, 2:1, 3:2, 4:3, 5:4, 6:5}  # sqlite Sun=0 → Mon=0
    DAY_NAMES = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

    matrix = {}
    for r in rows:
        d = DOW_MAP[r["dow"]]
        h = r["hour"]
        load = round(r["ops"] / cap * 100, 1)
        matrix[f"{d}_{h}"] = {"day": d, "hour": h, "load_pct": load, "ops": r["ops"]}

    return jsonify({
        "pvz_id": pvz_id,
        "capacity_per_hour": cap,
        "day_names": DAY_NAMES,
        "matrix": list(matrix.values())
    })

# ─── ROUTES: EXPORT CSV ───────────────────────────────────────────────────────
@app.route("/api/export/csv")
@login_required
def export_csv():
    # Re-use report_load logic but return CSV
    user = get_current_user()
    conn = get_db()

    date_from = request.args.get("date_from", "2025-03-01")
    date_to   = request.args.get("date_to",   "2025-03-31")
    pvz_filter  = request.args.get("pvz_id")
    type_filter = request.args.get("type")
    region_filter = request.args.get("region")

    conditions = ["DATE(o.ts) BETWEEN ? AND ?"]
    params = [date_from, date_to]

    if user["role"] == "operator":
        conditions.append("o.pvz_id=?")
        params.append(user["pvz_id"])
    elif user["role"] == "supervisor":
        pvz_ids = [r[0] for r in conn.execute(
            "SELECT pvz_id FROM pvz WHERE region=?", (user.get("region",""),)
        ).fetchall()]
        if pvz_ids:
            conditions.append(f"o.pvz_id IN ({','.join('?'*len(pvz_ids))})")
            params.extend(pvz_ids)

    if pvz_filter:
        conditions.append("o.pvz_id=?")
        params.append(int(pvz_filter))
    if type_filter and type_filter in ("in","out","return"):
        conditions.append("o.type=?")
        params.append(type_filter)
    if region_filter:
        conditions.append("p.region=?")
        params.append(region_filter)

    where = "WHERE " + " AND ".join(conditions)
    rows = conn.execute(f"""
        SELECT o.pvz_id, p.address, p.capacity_per_hour,
               DATE(o.ts) AS date,
               CAST(strftime('%H', o.ts) AS INTEGER) AS hour,
               COUNT(*) AS ops
        FROM operations o JOIN pvz p ON o.pvz_id=p.pvz_id
        {where}
        GROUP BY o.pvz_id, date, hour
        ORDER BY o.pvz_id, date, hour
    """, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["pvz_id","address","date","hour","ops","capacity","load"])
    for r in rows:
        cap = r["capacity_per_hour"]
        ops = r["ops"]
        load = round(ops/cap, 4) if cap else 0
        writer.writerow([r["pvz_id"], r["address"], r["date"], r["hour"], ops, cap, load])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"pvz_load_{date_from}_{date_to}.csv"
    )

# ─── ROUTES: ERROR LOG ────────────────────────────────────────────────────────
@app.route("/api/errors")
@role_required("analyst", "supervisor")
def get_errors():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM error_log ORDER BY logged_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─── ROUTE: FRONTEND ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
