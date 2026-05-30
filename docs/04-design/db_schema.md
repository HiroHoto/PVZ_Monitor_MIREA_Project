# DOC-DES-002 — Схема базы данных

| Версия | Статус | Дата создания | Дата обновления |
|--------|--------|---------------|-----------------|
| v1.1   | Draft  | 2026-05-07    | 2026-05-30      |

О документе: физическая схема базы данных SQLite системы PVZ Monitor — таблицы, колонки, ограничения, связи.

Для кого: backend-разработчики, тестировщик.

Основано на: [ER-диаграмме](er_diagram.md), [логической модели](../05-data-and-integration/logical_data_model.md).

---

## Авторы документа

- Безручко Александр Вадимович — Backend Developer — проектирование БД

## История изменений

- [v1.0] [2026-05-07] (Безручко): первичная схема БД (pvz, schedule, operations, error_log).
- [v1.1] [2026-05-30] (Безручко): добавлены колонки `product_name`, `weight_kg` в таблицу `operations`; обновлён DDL с CONSTRAINT и DEFAULT.

---

## Таблицы

### `pvz` — Пункты выдачи заказов

| Поле               | Тип     | Ограничения                         | Описание                              |
|--------------------|---------|--------------------------------------|---------------------------------------|
| `pvz_id`           | INTEGER | PRIMARY KEY                          | Уникальный идентификатор ПВЗ          |
| `address`          | TEXT    | NOT NULL                             | Адрес точки                           |
| `capacity_per_hour`| INTEGER | NOT NULL, CHECK > 0                  | Пропускная способность (операций/час)  |
| `region`           | TEXT    | NOT NULL, DEFAULT 'Нет региона'      | Регион для группировки                |

### `schedule` — Расписание работы ПВЗ

| Поле        | Тип     | Ограничения                                   | Описание                     |
|-------------|---------|-----------------------------------------------|------------------------------|
| `id`        | INTEGER | PRIMARY KEY AUTOINCREMENT                     | Идентификатор записи         |
| `pvz_id`    | INTEGER | NOT NULL, REFERENCES pvz(pvz_id)             | Ссылка на ПВЗ                |
| `weekday`   | INTEGER | NOT NULL, CHECK (weekday BETWEEN 0 AND 6)     | День недели (0=пн … 6=вс)   |
| `open_time` | TEXT    | NOT NULL                                       | Время открытия (HH:MM)      |
| `close_time`| TEXT    | NOT NULL                                       | Время закрытия (HH:MM)      |
|           |         | CHECK (open_time < close_time)                 | Закрытие позже открытия     |

### `operations` — Операции ПВЗ

| Поле          | Тип     | Ограничения                                        | Описание                              |
|---------------|---------|----------------------------------------------------|---------------------------------------|
| `op_id`       | INTEGER | PRIMARY KEY                                        | Идентификатор операции                |
| `pvz_id`      | INTEGER | NOT NULL, REFERENCES pvz(pvz_id)                  | Ссылка на ПВЗ                         |
| `ts`          | TEXT    | NOT NULL                                           | Метка времени (ISO 8601)              |
| `type`        | TEXT    | NOT NULL, CHECK (type IN ('in','out','return'))    | Тип операции                          |
| `product_name`| TEXT    | NOT NULL, DEFAULT 'Не указан'                      | Наименование товара (≤200 симв.)      |
| `weight_kg`   | REAL    | NOT NULL, DEFAULT 0.0, CHECK (weight_kg >= 0)     | Вес товара в килограммах              |

### `error_log` — Журнал ошибок валидации

| Поле       | Тип     | Ограничения                    | Описание                              |
|------------|---------|--------------------------------|---------------------------------------|
| `id`       | INTEGER | PRIMARY KEY AUTOINCREMENT      | Идентификатор записи лога             |
| `pvz_id`   | INTEGER |                                | ПВЗ, для которого была попытка        |
| `ts`       | TEXT    |                                | Время попытки операции                |
| `op_type`  | TEXT    |                                | Тип операции из запроса               |
| `reason`   | TEXT    |                                | Причина отказа                        |
| `logged_at`| TEXT    | DEFAULT (datetime('now'))      | Время записи в лог                    |

---

## SQL DDL

```sql
CREATE TABLE IF NOT EXISTS pvz (
    pvz_id            INTEGER PRIMARY KEY,
    address           TEXT    NOT NULL,
    capacity_per_hour INTEGER NOT NULL CHECK(capacity_per_hour > 0),
    region            TEXT    NOT NULL DEFAULT 'Нет региона'
);

CREATE TABLE IF NOT EXISTS schedule (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pvz_id     INTEGER NOT NULL REFERENCES pvz(pvz_id),
    weekday    INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
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
```

---

## Связи

| Связь                | Тип | Описание                                            |
|----------------------|-----|-----------------------------------------------------|
| `pvz` → `schedule`   | 1:N | У одного ПВЗ несколько записей расписания по дням  |
| `pvz` → `operations` | 1:N | Один ПВЗ выполняет множество операций               |
| `pvz` → `error_log`  | 1:N | Один ПВЗ может иметь несколько записей в логе ошибок|

---

## Миграция БД

Функция `migrate_db()` в [`db.py`](../../db.py:94) автоматически добавляет колонки `product_name` и `weight_kg` в таблицу `operations`, если они отсутствуют:

```python
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
```

> **Ответственный за миграцию:** Безручко А.В. (Backend Developer)
