# Схема БД

## Таблицы
- **pvz** (id, address, capacity_per_hour)
- **schedule** (id, pvz_id, weekday, open_time, close_time)
- **operations** (id, pvz_id, ts, type)

## Связи
- 1:N между pvz и schedule по полю pvz_id.
- 1:N между pvz и operations по полю pvz_id.