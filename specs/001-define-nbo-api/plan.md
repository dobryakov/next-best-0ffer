# Implementation Plan: Next Best Offer API

**Branch**: `001-define-nbo-api` | **Date**: 2025-11-09 | **Spec**: `specs/001-define-nbo-api/spec.md`
**Input**: Feature specification from `/specs/001-define-nbo-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Реализуем контейнеризированный ML-сервис Next Best Offer: публичный REST API для управления покупателями, продуктами и событиями, асинхронный расчёт рекомендаций и выдача NBO с пояснением причин. Расчёт основан на двухэтапном ML-подходе: генерация кандидатов коллаборативной фильтрацией (ALS) и ранжирование градиентным бустингом с бизнес-ограничениями.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (API, воркеры), SQL (PostgreSQL)  
**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Celery, Redis, scikit-learn, implicit (ALS), LightGBM, Feast  
**Storage**: PostgreSQL (транзакционные данные), Redis (очередь/кэш), S3-совместимое хранилище артефактов, Feast feature store  
**Testing**: pytest, pytest-asyncio, great_expectations (данные), locust (нагрузка)  
**Target Platform**: Linux (docker-compose, Kubernetes-ready)
**Project Type**: Много сервисов (backend API + асинхронные воркеры + ML pipelines)  
**Performance Goals**: API 95-й перцентиль < 2 секунд для POST/PUT; выдача готовых рекомендаций с первого запроса ≥85%  
**Constraints**: Только opensource стек; асинхронность расчёта; обязательная трассировка и health-check  
**Scale/Scope**: 10k покупателей, 100k SKU, до 50 событий/сек, очередь расчётов до 5k активных задач

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Принцип I — ✅ Архитектура микросервисная: FastAPI API, Celery воркеры, ML pipelines отделены; REST-контракты включают `reason` и коды retry.
- Принцип II — ✅ Все компоненты планируются как docker-контейнеры; используется полностью opensource стек.
- Принцип III — ✅ Продуманы структурированные логи с trace id, метрики очередей, health-check endpoints.
- Принцип IV — ✅ Переменные окружения описываются в README/quickstart, документация ведётся на русском, даются curl-примеры.
- Принцип V — ✅ Планируются юнит, интеграционные и нагрузочные тесты; ML-метрики HitRate@K, Precision@K, MRR, Coverage, Diversity, а также A/B тесты.

*Re-check после Phase 1: отклонений принципов не выявлено.*

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
services/
├── api/
│   ├── app/                 # FastAPI приложение, валидации и контроллеры
│   ├── domain/              # use-cases и бизнес-логика
│   ├── infra/               # адаптеры PostgreSQL/Redis/Feature Store
│   └── tests/
├── workers/
│   ├── tasks/               # Celery задачи расчёта и обогащения
│   ├── pipelines/           # ML pipelines подготовки данных
│   └── tests/
├── ml/
│   ├── training/            # скрипты обучения ALS и LightGBM
│   ├── evaluation/          # ноутбуки/скрипты метрик
│   └── registry/            # управление версиями моделей
├── clients/
│   ├── cli/                 # shell/curl примеры
│   └── sdk-js/              # JS SDK и автотесты

tests/
├── contract/                # Проверка OpenAPI
├── integration/             # end-to-end сценарии (docker-compose)
└── performance/             # нагрузочные профили Locust
```

**Structure Decision**: Используем много-сервисную структуру `services/` с отдельными каталогами для API, воркеров и ML-пайплайнов, плюс клиенты и централизованные тестовые пакеты в корне `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
