# Quickstart — Next Best Offer API

## 1. Требования

- Docker 24+, docker-compose v2
- 8 GB RAM, 4 vCPU
- Доступ к интернету для загрузки opensource образов

## 2. Переменные окружения (.env)

Создайте файл `.env` в корне и заполните:

```env
POSTGRES_DSN=postgresql://nbo:nbo@postgres:5432/nbo
REDIS_URL=redis://redis:6379/0
FEAST_REPO_PATH=/opt/feast_repo
MODEL_REGISTRY_PATH=/opt/models
ALS_FACTORS=64
ALS_REG=0.1
LGBM_MODEL_PATH=/opt/models/lgbm.bin
LOG_LEVEL=INFO
API_PORT=9090
NBO_RETRY_WINDOW_SECONDS=30
EVENT_IDEMPOTENCY_WINDOW_SECONDS=600
AB_VARIANTS=control,treatmentA
```

При изменении/добавлении переменных обновляйте README и документацию.

## 3. Запуск сервисов

```bash
docker compose up --build api workers ml-pipeline
```

- `api` — FastAPI с REST-эндпоинтами (`/customers`, `/products`, `/events`, `/nbo/{customer_id}`)
- `workers` — Celery workers, выполняющие расчёт NBO и обновление признаков
- `ml-pipeline` — периодическое обучение ALS и LightGBM (cron/Prefect)

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

# нагрузочные
docker compose run --rm perf locust -f load/locustfile.py --headless -u 100 -r 10
```

## 7. ML-пайплайн

- ALS (implicit) пересчитывается ежечасно: `docker compose run --rm ml-pipeline python -m pipelines.train_als --mode=batch`
- LightGBM обновляется ежедневно: `docker compose run --rm ml-pipeline python -m pipelines.train_ranker`
- Метрики качества пишутся в PostgreSQL и публикуются через `/metrics/ml`.

## 8. Наблюдаемость

- Логи доступны через `docker compose logs -f api` и `workers`
- Метрики Prometheus на `http://localhost:9090`
- Трассировки отправляются в Jaeger (`http://localhost:16686`)

## 9. A/B тестирование

- Перед запросом рекомендаций передавайте `variant` (`control`, `treatmentA`)
- Результаты эксперимента сохраняются в таблице `experiments_results` и доступны через BI.

