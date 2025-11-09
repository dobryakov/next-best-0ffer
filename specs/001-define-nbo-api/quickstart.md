# Quickstart — Next Best Offer API

## 1. Требования

- Docker 24+, docker-compose v2
- 8 GB RAM, 4 vCPU
- Доступ к интернету для загрузки opensource образов

## 2. Переменные окружения (.env)

Скопируйте пример и при необходимости адаптируйте значения:

```bash
cp .env.example .env
```

Расшифровки и рекомендации по настройке см. в `docs/configuration/env.md`.
При добавлении новых переменных синхронизируйте `.env.example`, README и документацию.

## 3. Запуск сервисов

Перед запуском пересоберите образы после изменения зависимостей:

```bash
docker compose build api workers ml-pipeline
```

Запустите основные сервисы:

```bash
docker compose up --build api workers ml-pipeline
```

- `api` — FastAPI с REST-эндпоинтами (`/customers`, `/products`, `/events`, `/nbo/{customer_id}`)
- `workers` — Celery workers, выполняющие расчёт NBO и обновление признаков
- `ml-pipeline` — периодическое обучение ALS и LightGBM (cron/Prefect)

### 3.1 Celery-воркеры

> ⚠️ Контейнер `workers` использует `.env` для подключения к Redis/PostgreSQL и списку Celery-импортов — перед запуском убедитесь, что файл актуален.

- Пересобрать образ воркеров после изменения зависимостей:

  ```bash
  docker compose build workers
  ```

- Запустить воркеры в фоне (оставит логи в текущем терминале):

  ```bash
  docker compose up workers
  ```

- Запустить воркеры с нужным уровнем логирования и масштабированием:

  ```bash
  LOG_LEVEL=DEBUG docker compose up -d --scale workers=2 workers
  ```

- Проверить готовность воркеров:

  ```bash
  docker compose exec workers celery --app services.workers.tasks.celery_app inspect ping
  ```

## 4. Первичная инициализация данных

```bash
docker compose run --rm api python -m scripts.bootstrap_db
docker compose run --rm ml-pipeline python -m pipelines.load_sample_catalog
docker compose run --rm ml-pipeline python -m pipelines.train_models --mode=initial
```

## 5. Проверка работоспособности

```bash
# health-check
curl -s http://localhost:9090/health | jq

# создать покупателя
curl -s -X POST http://localhost:9090/customers \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "11111111-1111-1111-1111-111111111111",
    "email": "user@example.com",
    "segments": ["electronics", "vip"]
  }' | jq

# зафиксировать событие
curl -s -X POST http://localhost:9090/events \
  -H 'Content-Type: application/json' \
  -d '{
    "category": "view",
    "customer_id": "11111111-1111-1111-1111-111111111111",
    "product_ids": ["SKU-001"],
    "channel": "web",
    "occurred_at": "2025-11-09T10:00:00Z"
  }'

# запросить рекомендацию
curl -s http://localhost:9090/nbo/11111111-1111-1111-1111-111111111111 | jq
```

## 6. Тесты

> ⚠️ Перед запуском любых `docker compose run ...` обязательно пересобирайте образ соответствующего сервиса:  
> `docker compose build <service>` (например, `docker compose build api`).  
> Это гарантирует, что контейнер видит актуальный код и не требует дополнительных volume-маппингов.

```bash
# юнит + интеграционные тесты
docker compose run --rm api pytest
docker compose run --rm workers pytest

# контракты OpenAPI
docker compose run --rm api pytest -m contract

# нагрузочные (прогрев включает сценарии из tests/performance/locustfile.py)
docker compose --profile perf run --rm perf \
  --headless --users 25 --spawn-rate 5 --run-time 5m
```

## 7. ML-пайплайн

- ALS (implicit) пересчитывается ежечасно: `docker compose run --rm ml-pipeline python -m pipelines.train_als --mode=batch`
- LightGBM обновляется ежедневно: `docker compose run --rm ml-pipeline python -m pipelines.train_ranker`
- Метрики качества пишутся в PostgreSQL и публикуются через `/metrics/ml`.

## 8. Наблюдаемость

- Логи доступны через `docker compose logs -f api workers`
- Метрики Prometheus на `http://localhost:${METRICS_PORT:-9091}/metrics`
- Трассировки отправляются в Jaeger (`TRACING_ENDPOINT`, см. `.env`)

## 9. A/B тестирование

- Перед запросом рекомендаций передавайте `variant` (`control`, `treatmentA`)
- Результаты эксперимента сохраняются в таблице `experiments_results` и доступны через BI.

## 10. Клиенты и примеры

- Shell-скрипты: `clients/cli/*.sh`
- Пример PHP SDK: `clients/php`
- JS SDK: `clients/sdk-js`

Перед использованием убедитесь, что сервисы из раздела 3 запущены,
а переменные окружения настроены согласно `docs/configuration/env.md`.

