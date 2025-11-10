# 🚀 Next Best Offer Platform — ваш ускоритель роста конверсии и LTV

Представьте себе продукт, который знает вашего клиента лучше, чем он сам: именно так работает наша Next Best Offer Platform. Она соединяет богатую поведенческую аналитику, real-time обработку событий и продвинутые ML-модели (ALS, LightGBM, feature store на Feast), чтобы выдавать персональные рекомендации с первой секунды. Система построена на стекe FastAPI, Celery, PostgreSQL, Redis и оркестрируется через Docker Compose — всё для масштабирования без боли и остановок. Бизнес получает прозрачную воронку рекомендаций, измеримые uplift-показатели и гибкую настройку стратегий удержания, а маркетинг — готовые сценарии, которые можно A/B-тестировать, запускать в performance-каналах и интегрировать в CRM. Добавьте к этому наблюдаемость, auto-healing health-checks и автоматизированные пайплайны обучения — и вы получите платформу, которая превращает данные в деньги.

## Next Best Offer Platform

Контейнеризированный сервис рекомендаций с REST API, асинхронными воркерами
и ML-пайплайнами для расчёта Next Best Offer.

## Сервисы и инфраструктура

- `api` — FastAPI сервис, реализующий эндпоинты `/customers`, `/events`, `/nbo/{customer_id}` и health-check.
- `workers` — Celery-воркеры, обрабатывающие события и выполняющие расчёт рекомендаций.
- `ml-pipeline` — задания подготовки фичей, обучения ALS/LightGBM и загрузки моделей.
- `postgres`, `redis`, `feast` — инфраструктурные компоненты для хранения данных и признаков.
- `perf` (docker profile `perf`) — контейнер с Locust для нагрузочного профилирования API.

Архитектура и детали реализации описаны в `specs/001-define-nbo-api/plan.md`.

## Быстрый старт

Подробный гайд и примеры находятся в `specs/001-define-nbo-api/quickstart.md`. Краткий чек-лист:

- Скопируйте `.env` из шаблона и заполните обязательные переменные (`POSTGRES_DSN`, `REDIS_URL`, см. `docs/configuration/env.md`).
- Соберите/обновите образы приложений, подтяните инфраструктурные образы.
- Поднимите `postgres`, `redis`, `feast`, дождитесь health-check’ов.
- Примените миграции `alembic upgrade head` внутри контейнера `api`.
- Запустите `api`, `workers`, `ml-pipeline`.

```bash
docker compose pull postgres redis feast
docker compose build api workers ml-pipeline
docker compose up -d postgres redis feast
docker compose run --rm api alembic upgrade head
docker compose up -d api workers ml-pipeline
```

Инициализация демонстрационных данных и обучение стартовых моделей:

```bash
docker compose run --rm ml-pipeline python -m pipelines.load_sample_catalog
docker compose run --rm ml-pipeline python -m pipelines.train_models --mode=initial
```

- _(Временное примечание до закрытия задач T051/T052: если автоматический шедулер ещё не внедрён, внесите команды пересчёта моделей в cron/systemd timer вручную и удалите этот пункт после появления шедулера.)_

### Celery-воркеры

- Пересобрать образ после обновления зависимостей воркеров:

  ```bash
  docker compose build workers
  ```

- Запустить Celery-воркеры в foreground-режиме для отладки:

  ```bash
  docker compose up workers
  ```

- Масштабировать и запустить воркеры в фоне с повышенным уровнем логирования:

  ```bash
  LOG_LEVEL=DEBUG docker compose up -d --scale workers=2 workers
  ```

- Проверить, что воркеры отвечают на ping:

  ```bash
  docker compose exec workers celery --app services.workers.tasks.celery_app inspect ping
  ```

## Тестирование

```bash
# Юнит и интеграционные тесты API
docker compose run --rm api pytest

# Контрактные тесты OpenAPI
docker compose run --rm api pytest -m contract

# Тесты воркеров
docker compose run --rm workers pytest

# Нагрузочное профилирование (Locust, включает прогрев данных)
docker compose --profile perf run --rm perf \
  --headless --users 25 --spawn-rate 5 --run-time 5m
```

Дополнительные сценарии тестирования описаны в `tests/performance/locustfile.py`.

## Наблюдаемость и мониторинг

- Логи: `docker compose logs -f api workers`
- Метрики: Prometheus экспорт в API (`http://localhost:${METRICS_PORT:-9091}/metrics`)
- Трассировки: Jaeger (`TRACING_ENDPOINT`), подробнее в `docs/monitoring/nbo-dashboard.md`

## Клиенты

- Shell-утилиты: `clients/cli/*.sh`
- PHP SDK-пример: `clients/php`
- JS SDK-пример: `clients/sdk-js`

Перед использованием внимательно изучите `docs/configuration/env.md`
(`@env.md`) с описанием переменных окружения, значений для `.env` и требований к инфраструктуре.

## CI/CD

Workflow `.github/workflows/ci.yml` выполняет:

- линтеры/тесты API и воркеров внутри контейнеров;
- проверку контрактов OpenAPI;
- smoke-нагрузку через Locust (headless профиль `perf`).

Добавляйте новые проверки по мере расширения функциональности.
