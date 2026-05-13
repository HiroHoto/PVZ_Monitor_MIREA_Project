# ER-диаграмма (модель данных)

## Сущности и атрибуты
- **pvz** (id, address, capacity_per_hour)
- **schedule** (id, pvz_id, weekday, open_time, close_time)
- **operations** (id, pvz_id, ts, type)

## Связи
- 1:N между pvz и schedule по полю pvz_id.
- 1:N между pvz и operations по полю pvz_id.

## Mermaid-схема
![ER Diagram](data_model.er)
erDiagram
    pvz {
        int pvz_id PK
        string address
        int capacity_per_hour
        string region
    }
    schedule {
        int id PK
        int pvz_id FK
        string weekday
        string open_time
        string close_time
    }
    operations {
        int op_id PK
        int pvz_id FK
        datetime ts
        string type
    }
    error_log {
        int id PK
        int pvz_id
        datetime ts
        string op_type
        string reason
        datetime logged_at
    }
    pvz ||--o{ schedule : "1:N"
    pvz ||--o{ operations : "1:N"