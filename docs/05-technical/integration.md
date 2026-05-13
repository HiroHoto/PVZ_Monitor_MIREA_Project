# Интеграция с внешней системой (1С:Склад)

**Сценарий:** Получение данных о выдаче заказа.

| Поле источника (1С) | Поле ПВЗ Monitor | Тип данных | Правило трансформации |
| :--- | :--- | :--- | :--- |
| `DocID` | `op_id` | String | Префикс '1C-' + ID |
| `PointCode` | `pvz_id` | Integer | Прямое соответствие |
| `OperationDate` | `ts` | DateTime | ISO 8601 |
| `ActionType` | `type` | Enum | 'Shipment' -> 'out', 'Return' -> 'return' |