# Event Storming (текстовое описание)

## События (Events)
- `OperationRegistered` — операция успешно записана в БД.
- `ValidationFailed` — операция отклонена (причина: неверный тип, ПВЗ закрыт и т.д.).
- `LoadThresholdExceeded` — загрузка превысила 85%.
- `CriticalOverloadDetected` — загрузка превысила 120%.
- `ReportGenerated` — сформирован аналитический отчет.
- `CSVExported` — данные успешно выгружены в файл.

## Команды (Commands)
- `RegisterOperation` — инициирует цепочку валидаций и запись.
- `CalculateLoad` — запускает пересчет KPI для ПВЗ.
- `GenerateReport` — запрос на формирование сводного отчета.
- `ExportData` — команда на выгрузку данных в CSV.
- `NotifySupervisor` — отправка уведомления при критической нагрузке.

## Агрегаты (Aggregates)
- ПВЗ связан с событиями загрузки и перегрузки:
  - Минимальная загрузка: 0%
  - Максимальная загрузка: 150%
  - Критический порог: >120%

## Схема
![Event Storming Diagram](../diagrams/event_storming_diagram.es)