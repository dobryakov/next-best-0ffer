# Tasks: Next Best Offer API

**Input**: Design documents from `/specs/001-define-nbo-api/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовить каркас репозитория и контейнеров для сервисов API, воркеров и ML пайплайнов.

- [X] T001 Создать каталоги и базовые `__init__.py` для структуры `services/api`, `services/workers`, `services/ml`, `clients/cli`, `clients/sdk-js` по плану в `services/`
- [X] T002 Описать сервисы `api`, `workers`, `ml-pipeline`, `postgres`, `redis`, `feast` в `docker-compose.yml`
- [X] T003 [P] Настроить Python-зависимости и скрипты сборки в `services/api/pyproject.toml` и `services/workers/pyproject.toml`
- [X] T004 [P] Сформировать `.env.example` и обновить переменные из quickstart в `.env.example`
- [X] T047 [P] Настроить зависимости ML-пайплайна в `services/ml/pyproject.toml` и обеспечить совместимость с API/Workers
- [X] T048 [P] Создать `services/ml/Dockerfile` и зафиксировать базовый образ, установку зависимостей и entrypoint для контейнера `ml-pipeline`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Настроить общую инфраструктуру: БД, очереди, конфигурацию и базовый FastAPI каркас.

- [X] T005 Инициализировать Alembic и общие настройки миграций в `services/api/infra/db/migrations/env.py`
- [X] T006 [P] Создать модуль подключения к БД и session factory в `services/api/infra/db/session.py`
- [X] T007 [P] Реализовать слой конфигурации с Pydantic Settings и загрузкой из `.env` в `services/api/infra/config/settings.py`
- [X] T008 [P] Настроить FastAPI приложение, маршрутизацию и зависимость настройки в `services/api/app/main.py`
- [X] T009 [P] Добавить middleware структурированного логирования, trace id и correlation id в `services/api/app/middleware/observability.py`
- [X] T010 Сконфигурировать Celery приложение и расписания задач в `services/workers/tasks/celery_app.py`
- [X] T011 [P] Описать общие параметры очередей и retry-политику в `services/workers/tasks/config.py`
- [X] T012 Реализовать health-check endpoint с проверкой PostgreSQL/Redis/Celery в `services/api/app/routes/health.py`

---

## Phase 3: User Story 1 — Управление данными покупателя (Priority: P1) 🎯 MVP

**Goal**: Обеспечить создание и обновление покупателей с валидацией атрибутов и аудитом изменений.
**Independent Test**: Отправить POST `/customers` и PUT `/customer/{id}` с полным набором полей и убедиться, что данные сохраняются и доступны повторно.

### Tests for User Story 1

- [X] T013 [P] [US1] Добавить контрактный тест POST/PUT `/customers` в `tests/contract/test_customers_contract.py`
- [X] T014 [P] [US1] Реализовать интеграционный сценарий создания и обновления покупателя в `tests/integration/test_customer_crud.py`

### Implementation for User Story 1

- [X] T015 [P] [US1] Создать миграцию таблицы `customers` с индексами и аудитом версий в `services/api/infra/db/migrations/versions/create_customers_table.py`
- [X] T016 [P] [US1] Определить SQLAlchemy-модель `Customer` и enum состояний в `services/api/infra/db/models/customer.py`
- [X] T017 [P] [US1] Реализовать репозиторий работы с покупателями и идемпотентность записей в `services/api/domain/customers/repository.py`
- [X] T018 [P] [US1] Создать сервис бизнес-логики обновления сегментов и аудит-логов в `services/api/domain/customers/service.py`
- [X] T019 [US1] Описать схемы запросов/ответов и валидацию атрибутов в `services/api/app/schemas/customer.py`
- [X] T020 [US1] Реализовать маршруты POST `/customers` и PUT `/customer/{id}` с логированием trace id в `services/api/app/routes/customers.py`
- [X] T021 [US1] Настроить протокол аудита версий и публикацию событий обновления в `services/api/domain/customers/audit.py`
- [X] T022 [US1] Обновить CLI-пример отправки запросов покупателей в `clients/cli/customers.sh`

---

## Phase 4: User Story 2 — Регистрация клиентских событий (Priority: P2)

**Goal**: Принимать и сохранять клиентские события, обеспечивать идемпотентность и постановку в очередь расчётов.
**Independent Test**: Отправить несколько категорий событий через POST `/events` и проверить запись в БД и публикацию задачи в очередь.

### Tests for User Story 2

- [X] T023 [P] [US2] Добавить контрактный тест POST `/events` с обязательными и дополнительными полями в `tests/contract/test_events_contract.py`
- [X] T024 [P] [US2] Реализовать интеграционный сценарий регистрации и дедупликации событий в `tests/integration/test_event_ingestion.py`

### Implementation for User Story 2

- [X] T025 [P] [US2] Создать миграцию таблицы `events` с foreign key и idempotency индексом в `services/api/infra/db/migrations/versions/create_events_table.py`
- [X] T026 [P] [US2] Определить модель `Event` с проверками категорий и каналов в `services/api/infra/db/models/event.py`
- [X] T027 [P] [US2] Реализовать репозиторий событий с вычислением детерминированного идентификатора в `services/api/domain/events/repository.py`
- [X] T028 [US2] Вынести генерацию токена идемпотентности и ограничения окна в `services/api/domain/events/idempotency.py`
- [X] T029 [US2] Реализовать маршрут POST `/events` с постановкой задач в очередь и ответом 202 в `services/api/app/routes/events.py`
- [X] T030 [US2] Создать Celery-задачу обогащения признаков и записи в feature store в `services/workers/tasks/events_ingest.py`
- [X] T031 [US2] Добавить метрики очереди событий и экспорт Prometheus в `services/workers/tasks/metrics.py`

---

## Phase 5: User Story 3 — Получение Next Best Offer (Priority: P3)

**Goal**: Выдавать рекомендации через GET `/nbo/{customer_id}` с асинхронным расчётом и пояснениями причин.
**Independent Test**: Запросить GET `/nbo/{customer_id}` при статусах `ready` и `pending`, проверить наличие поля `reason` и корректного retry.

### Tests for User Story 3

- [X] T032 [P] [US3] Добавить контрактный тест GET `/nbo/{customer_id}` на ответы 200/202/404 в `tests/contract/test_recommendations_contract.py`
- [X] T033 [P] [US3] Реализовать интеграционный сценарий полного расчёта NBO и повторного запроса в `tests/integration/test_nbo_flow.py`

### Implementation for User Story 3

- [X] T034 [P] [US3] Создать миграцию таблиц `recommendations` и `calculation_jobs` в `services/api/infra/db/migrations/versions/create_recommendations_table.py`
- [X] T035 [P] [US3] Описать модели `Recommendation` и `CalculationJob` с ограничениями статусов в `services/api/infra/db/models/recommendation.py`
- [X] T036 [P] [US3] Реализовать сервис оркестрации расчёта (ALS + LightGBM) и rerank правил в `services/api/domain/recommendations/service.py`
- [X] T037 [US3] Создать воркер-пайплайн генерации кандидатов и ранжирования в `services/workers/pipelines/recommendations_flow.py`
- [X] T038 [US3] Реализовать endpoint GET `/nbo/{customer_id}` с обработкой статусов и retry в `services/api/app/routes/recommendations.py`
- [X] T039 [US3] Добавить объяснения `reason` и контроль A/B вариантов в `services/api/domain/recommendations/explanations.py`
- [X] T040 [US3] Обновить OpenAPI спецификацию рекомендаций и статусов в `specs/001-define-nbo-api/contracts/openapi.yaml`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Завершить документацию, наблюдаемость и процессы.

- [X] T041 [P] Актуализировать quickstart и README с новыми командами в `specs/001-define-nbo-api/quickstart.md` и `README.md`
- [X] T042 [P] Добавить нагрузочные профили Locust и сценарии прогрева данных в `tests/performance/locustfile.py`
- [X] T043 [P] Пересмотреть `.env.example`, добавить описания переменных в `docs/configuration/env.md`
- [X] T044 Настроить CI-пайплайн с прогоном pytest, контрактных и нагрузочных smoke-тестов в `.github/workflows/ci.yml`
- [X] T045 [P] Описать дашборды мониторинга и алерты в `docs/monitoring/nbo-dashboard.md`
- [X] T046 Актуализировать shell-клиент (cli), php-клиент, и js-клиент (sdk-js) в `clients`
- [X] T049 [P] Подготовить Dockerfile для контейнера `workers` в `services/workers/Dockerfile` с установкой зависимостей и entrypoint для Celery
- [X] T050 Обновить документацию (`specs/001-define-nbo-api/quickstart.md`, `README.md`) с инструкциями по сборке и запуску контейнера `workers`
- [ ] T051 [P] Добавить сервис `scheduler` в `docker-compose.yml` для периодического запуска ALS и LightGBM пайплайнов
- [ ] T052 [P] Описать автоматический пересчёт моделей в `specs/001-define-nbo-api/quickstart.md` и `README.md`, включая требования к .env и командам cron
- [ ] T053 [P] Переписать JS-клиент как React-компонент для встраивания в приложения на React, учесть фронтенд-окружение без доступа к `.env`, описать альтернативные механизмы конфигурации и добавить примеры использования
- [ ] T054 [P] Переписать PHP-клиент как пакет для Symfony-приложений с сервис-провайдером, поддержкой DI и примерами интеграции

---

## Dependencies & Execution Order

- Иерархия фаз: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6.
- User Story 2 опирается на завершение Phase 2 и интеграцию с `customers` из Phase 3 (чтение FK), но тесты должны использовать подготовленные данные из независимых фикстур.
- User Story 3 требует наличия очередей и событий из Phase 4 для feed данных, однако endpoint должен корректно работать с загруженными фикстурами даже без живого воркера.

---

## Parallel Execution Examples

### User Story 1

Можно параллельно:
- Реализовывать модели и репозиторий (T016, T017) одновременно с разработкой схем (T019), поскольку файлы не пересекаются.
- Писать контрактный тест (T013) параллельно с миграцией (T015), чтобы валидировать контракт до запуска сервиса.

### User Story 2

Параллельно выполняются:
- Разработка Celery задачи (T030) и метрик (T031) без конфликтов.
- Настройка маршрута `/events` (T029) и выделение idempotency утилиты (T028).

### User Story 3

В параллель идут:
- Создание миграций (T034) и моделей (T035).
- Реализация сервиса оркестрации (T036) и воркер-пайплайна (T037) при согласованных контрактных интерфейсах.

---

## Implementation Strategy

- **MVP**: Завершить Phase 1–2 и User Story 1 (Phase 3) для базового CRUD покупателей и health-check.
- **Incremental Delivery**: После MVP добавить US2 для событий и асинхронных очередей, затем US3 для полной выдачи рекомендаций.
- **Validation**: После каждой фазы прогонять контрактные и интеграционные тесты из соответствующих `tests/` каталогов.


