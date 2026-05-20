# ПВЗ Monitor — Система управления загрузкой пунктов выдачи

## Описание проекта
Программный комплекс для мониторинга и оптимизации работы пунктов выдачи заказов (ПВЗ). Система позволяет сбалансировать нагрузку на точки выдачи, минимизировать очереди в пиковые часы и повысить эффективность работы персонала за счёт предиктивного анализа и оперативного информирования о перегрузках.

**Кейс:** Пункты выдачи маркетплейса (e-commerce / логистика).

## Целевые метрики (KPI)
- **Средняя загрузка в часы пик:** < 85% (пиковые часы: 12:00–14:00, 18:00–20:00).
- **Допустимая доля интервалов с перегрузкой:** ≤ 5% от общего рабочего времени.
- **Порог критической перегрузки:** > 120% от паспортной мощности.
- **Методика расчета:** `Загрузка = (Кол-во операций в час / Пропускная способность в час) * 100%`.

## Стек технологий
- **Backend:** Python 3.10, Flask 3.x, SQLite 3.
- **Frontend:** Vanilla JS (ES6+), HTML5, CSS3, Chart.js 4.4, Lucide Icons.
- **Архитектура:** REST API.

## Быстрый старт
```bash
# 1. Установка зависимостей
pip install -r requirements.txt

# 2. Запуск сервера (по умолчанию http://127.0.0.1:5000)
python app.py
```

## Документация
Полный пакет проектной документации расположен в директории `docs/`:
- **Governance:** [Карточка проекта](docs/00-governance/project_card.md), [RACI-матрица](docs/00-governance/raci_matrix.md).
- **Discovery:** [Описание проблемы](docs/01-discovery/problem_statement.md).
- **Requirements:** [User Stories](docs/02-requirements/user_stories.md), [MoSCoW-матрица](docs/02-requirements/moscow_matrix.md), [Feature List](docs/02-requirements/feature_list.md).
- **Planning:** [WBS](docs/03-planning/wbs.md), [Roadmap](docs/03-planning/roadmap.md), [Матрица рисков](docs/03-planning/risk_matrix.md).
- **Design:** [BPMN-процессы](docs/04-design/bpmn_description.md), [Схема БД](docs/04-design/db_schema.md), [ER-диаграмма](docs/04-design/er_diagram.md), [Event Storming](docs/04-design/event_storming.md), [Диаграмма состояний](docs/04-design/state_diagram.md).
- **Technical:** [Инструкция по развёртыванию](docs/05-technical/deployment.md), [API Контракт](docs/05-technical/api_contract.md).

## Команда проекта
| Роль | ФИО | Контакт |
|------|-----|---------|
| **Team Lead** | Рахимов Руслан Саидович | ruslan@example.com |
| **Backend Developer** | Безручко Александр Вадимович | alexander@example.com |
| **Backend Developer** | Юркив Альберт Александрович | albert@example.com |
| **Frontend Developer** | Углев Михаил Андреевич | mikhail@example.com |
| **Fullstack Developer** | Володин Никита Филиппович | nikita@example.com |

## Демо-аккаунты
| Логин | Пароль | Роль | Область доступа |
|-------|--------|------|-----------------|
| `operator1` | `op1pass` | Оператор | Только ПВЗ №1 |
| `operator2` | `op2pass` | Оператор | Только ПВЗ №2 |
| `supervisor1` | `suppass` | Супервайзер | Регион "Центральный" |
| `analyst1` | `anapass` | Аналитик | Все данные + экспорт |

## API Эндпоинты
| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | [`/api/login`](docs/05-technical/api_contract.md#post-apilogin) | Аутентификация пользователя |
| `POST` | [`/api/logout`](docs/05-technical/api_contract.md#post-apilogout) | Выход из системы |
| `GET` | [`/api/me`](docs/05-technical/api_contract.md#get-apime) | Данные текущего пользователя |
| `GET` | [`/api/pvz`](docs/05-technical/api_contract.md#get-apipvz) | Список ПВЗ (с фильтрацией по роли) |
| `GET` | [`/api/pvz/<id>`](docs/05-technical/api_contract.md#get-apipvzid) | Детали ПВЗ и расписание |
| `GET` | [`/api/regions`](docs/05-technical/api_contract.md#get-apiregions) | Список доступных регионов |
| `GET` | [`/api/operations`](docs/05-technical/api_contract.md#get-apioperations) | Журнал операций с фильтрами |
| `POST` | [`/api/operations`](docs/05-technical/api_contract.md#post-apioperations) | Регистрация новой операции |
| `GET` | [`/api/report/load`](docs/05-technical/api_contract.md#get-apireportload) | Отчёт о загрузке и KPI |
| `GET` | [`/api/report/heatmap`](docs/05-technical/api_contract.md#get-apireportheatmap) | Данные для тепловой карты |
| `GET` | [`/api/export/csv`](docs/05-technical/api_contract.md#get-apiexportcsv) | Экспорт данных в CSV |
| `GET` | [`/api/errors`](docs/05-technical/api_contract.md#get-apierrors) | Журнал ошибок валидации |

> Подробная спецификация: [api/openapi.yaml](api/openapi.yaml).

## Валидация данных
Система автоматически проверяет операции по 5 критериям:
1. **Existence:** Существование ПВЗ в системе.
2. **Schedule:** Соответствие рабочим дням недели.
3. **Working Hours:** Соответствие часам работы (открытие/закрытие).
4. **Operation Type:** Допустимые типы (`in`, `out`, `return`).
5. **Data Integrity:** Обязательность полей и корректность форматов.

## Тестирование
Для запуска автоматизированных тестов выполните команду:
```bash
pytest -v
```

## Структура репозитория
```
.
├── .github/
│   └── workflows/
│       └── tests.yml                    — CI/CD конфигурация для GitHub Actions
├── .pytest_cache/                       — Кэш pytest
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   ├── README.md
│   └── v/cache/
│       ├── lastfailed
│       ├── nodeids
│       └── stepwise
├── .vs/                                 — Visual Studio конфигурация
│   ├── ProjectSettings.json
│   ├── PythonSettings.json
│   ├── slnx.sqlite
│   ├── VSWorkspaceState.json
│   └── Project.slnx/
│       ├── FileContentIndex/
│       │   ├── 6c39df2e-475a-4254-840a-400c659503e3.vsidx
│       │   └── 19220dca-feba-45fe-967d-45d4f0662988.vsidx
│       └── v18/
│           ├── .wsuo
│           ├── DocumentLayout.backup.json
│           └── DocumentLayout.json
├── api/
│   └── openapi.yaml                     — OpenAPI спецификация REST API
├── data/
│   ├── operations.json                  — Справочник операций
│   ├── pvz.json                         — Справочник пунктов выдачи
│   └── schedule.json                    — Расписание работы ПВЗ
├── diagrams/
│   ├── business_process.bpmn            — BPMN диаграмма бизнес-процессов
│   └── event_storming_diagram.es        — Event Storming диаграмма
├── docs/
│   ├── map.md                           — Карта документации
│   ├── README.md                        — Описание документации
│   ├── 00-governance/
│   │   ├── project_card.md              — Карточка проекта
│   │   ├── raci_matrix.md               — RACI-матрица ответственности
│   │   └── task_distribution.md         — Распределение задач
│   ├── 01-discovery/
│   │   └── problem_statement.md         — Описание проблемы
│   ├── 02-requirements/
│   │   ├── feature_list.md              — Список функций
│   │   ├── moscow_matrix.md             — MoSCoW-матрица приоритизации
│   │   └── user_stories.md              — User Stories
│   ├── 03-planning/
│   │   ├── risk_matrix.md               — Матрица рисков
│   │   ├── roadmap.md                   — Дорожная карта проекта
│   │   └── wbs.md                       — Work Breakdown Structure
│   ├── 04-design/
│   │   ├── bpmn_description.md          — Описание BPMN-процессов
│   │   ├── business_process.bpmn        — BPMN диаграмма
│   │   ├── data_model.er                — ER-модель данных
│   │   ├── db_schema.md                 — Схема базы данных
│   │   ├── er_diagram.md                — ER-диаграмма
│   │   ├── event_storming_diagram.es    — Event Storming диаграмма
│   │   ├── event_storming.md            — Описание Event Storming
│   │   ├── heatmap_dashboard.md         — Дизайн тепловой карты
│   │   └── state_diagram.md             — Диаграмма состояний
│   ├── 04-testing/
│   │   └── test_plan.md                 — План тестирования
│   ├── 05-technical/
│   │   ├── api_contract.md              — API контракт и спецификация
│   │   └── deployment.md                — Инструкция по развёртыванию
│   └── 90-checkpoints/
│       ├── CP1_status.md                — Статус контрольной точки 1
│       ├── CP2_status.md                — Статус контрольной точки 2
│       └── CP3_status.md                — Статус контрольной точки 3
├── routes/
│   ├── __init__.py                      — Инициализация пакета routes
│   ├── auth.py                          — Маршруты аутентификации
│   ├── operations.py                    — Маршруты операций
│   ├── pvz.py                           — Маршруты ПВЗ
│   └── reports.py                       — Маршруты отчётов
├── templates/
│   └── index.html                       — Главный HTML-шаблон фронтенда
├── tests/
│   ├── conftest.py                      — Конфигурация pytest
│   ├── test_auth.py                     — Тесты аутентификации
│   └── test_operations.py               — Тесты операций
├── .gitattributes                       — Атрибуты Git
├── .gitignore                           — Исключения Git
├── app.py                               — Основной файл приложения Flask
├── auth.py                              — Модуль аутентификации и авторизации
├── config.py                            — Конфигурация приложения и пользователи
├── db.py                                — Инициализация и работа с БД SQLite
├── FEATURE_LIST.md                      — Список реализованных функций
├── generate_realistic_data.py           — Скрипт генерации тестовых данных
├── LICENSE.txt                          — Лицензия проекта
├── nano.bat                             — Батник для редактирования файлов
├── pvz.db                               — База данных SQLite
├── README.md                            — Этот файл (основная документация)
├── requirements.txt                     — Зависимости Python
├── SRS.md                               — Software Requirements Specification
└── TASKS.md                             — Список задач проекта
```
