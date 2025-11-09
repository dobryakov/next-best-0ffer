# Мониторинг Next Best Offer

Документ описывает рекомендуемые дашборды и алерты для контроля работы платформы.
Метрики собираются сервисами API и воркерами (Prometheus), а также из ML пайплайнов.

## 1. Обзорный дашборд (Executive Summary)

| Виджет | Метрика | Цель/порог |
|--------|---------|------------|
| SLA API | `http_request_duration_ms` p95, `http_requests_total` (2xx/4xx/5xx) | p95 < 2s, ошибок < 1% |
| Health | `/health` status, uptime контейнеров | Все сервисы в состоянии `healthy` |
| Конверсия NBO | `nbo_recommendation_jobs_completed_total{outcome="ready"}` / `...{outcome="pending"}` | ≥85% готовых рекомендаций с первого запроса |

## 2. API Performance

- **Latency**: развернуть гистограммы `http_request_duration_ms` (p50/p95/p99) по методам.
- **Error rate**: предупреждение при `5xx` > 0.5% за 5 минут.
- **Trace drill-down**: ссылки из графиков на Jaeger по `trace_id`.

### Алерты

1. `API_HIGH_LATENCY`: p95 > 2s в течение 5 минут.
2. `API_ERROR_BURST`: 5xx > 20 за 1 минуту.
3. `API_NO_TRAFFIC`: отсутствует трафик > 10 минут (интеграция нарушена).

## 3. Очередь событий и воркеры

Используем метрики из `services/workers/tasks/metrics.py`.

| Метрика | Описание | Алерт |
|---------|----------|-------|
| `nbo_events_enqueued_total{category}` | События, поставленные в очередь. | Spike > 3σ или резкое падение (нет событий). |
| `nbo_events_processing_duration_seconds` | Длительность обработки. | p95 > 10s. |
| `nbo_events_processing_completed_total{outcome="failed"}` | Ошибки обработки. | > 5 ошибок / 5 мин. |

Рекомендуется выводить stacked-area график загрузки очередей и bar chart по outcomes.

## 4. Расчёт рекомендаций

- `nbo_recommendation_jobs_scheduled_total{channel,variant}` — мониторинг поступления задач.
- `nbo_recommendation_job_latency_seconds` — целевой p95 < 30s.
- `nbo_recommendation_jobs_completed_total{outcome}` — распределение успешных/failed/pending.

### Алерты

1. `NBO_LATENCY_SLA`: p95 > 30s (10 мин подряд).
2. `NBO_FAIL_RATE`: доля `outcome="failed"` > 5% за 15 мин.
3. `NBO_NO_JOBS`: отсутствие новых задач > 15 мин при наличии событий.

## 5. ML-качество (offline)

Интегрируйте выгрузки метрик (HitRate@5, MRR, Diversity) в Prometheus/Grafana:

- Линии с целевыми значениями (HitRate ≥ 0.35, MRR ≥ 0.25).
- Алерт `ML_QUALITY_DROP`: падение на >10% от среднего за последние 7 дней.

## 6. Логи и трассировки

- Используйте поля `trace_id` и `correlation_id`, добавленные middleware, для склейки логов API и воркеров.
- Настройте выборку ошибок уровня `ERROR` с фильтрацией по `service`.
- Отдельный виджет: последние 10 ошибочных трасс (Jaeger).

## 7. Данные для A/B экспериментов

- Метрика: `nbo_recommendation_jobs_completed_total{variant, outcome="ready"}`.
- Графики: конверсия по вариантам, доверительные интервалы.
- Алерт `AB_VARIANT_STALLED`: отсутствие данных по варианту > 30 мин (например, эксперимент выключен).

## 8. Интеграция с уведомлениями

| Канал | Алерты |
|-------|--------|
| Slack/Teams | SLA, очереди, ошибки воркеров |
| PagerDuty | API недоступен, Latency SLA нарушен, high fail rate |
| Email | Ежедневные отчёты ML-качества, A/B результаты |

Пересматривайте пороги ежемесячно и после крупных релизов,
фиксируйте изменения в этом документе и в конфигурации мониторинга.

