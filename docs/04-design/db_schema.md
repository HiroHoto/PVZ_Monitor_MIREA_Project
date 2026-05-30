# Схема БД

## Таблицы
- **pvz** (
    - pvz_id (PK)
    - address
    - capacity_per_hour
    - region
)
- **schedule** (
    - id (PK)
    - pvz_id (FK)
    - weekday
    - open_time
    - close_time
)
- **operations** (
    - op_id (PK)
    - pvz_id (FK)
    - ts
    - type
    - product_name — наименование товара (TEXT, NOT NULL, DEFAULT 'Не указан')
    - weight_kg — вес товара в кг (REAL, NOT NULL, DEFAULT 0.0, CHECK ≥ 0)
)
- **error_log** (
    - id (PK)
    - pvz_id
    - ts
    - op_type
    - reason
    - logged_at
)

## Связи
- 1:N между pvz и schedule по полю pvz_id.
- 1:N между pvz и operations по полю pvz_id.