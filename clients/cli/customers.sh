#!/usr/bin/env bash

# Примеры запросов к API управления покупателями.

set -euo pipefail

API_URL="${API_URL:-http://localhost:9090}"
TRACE_ID_HEADER="X-Trace-Id"

trace_id() {
  tr -d '\n' < /proc/sys/kernel/random/uuid
}

create_customer() {
  local customer_id payload trace
  customer_id="${1:-$(trace_id)}"
  trace="$(trace_id)"
  payload=$(cat <<JSON
{
  "id": "${customer_id}",
  "email": "customer@example.com",
  "phone": "+12345678901",
  "name": "Новый Покупатель",
  "segments": ["electronics", "vip"],
  "attributes": {"preferred_channel": "email"}
}
JSON
)

  curl -sS -H "Content-Type: application/json" -H "${TRACE_ID_HEADER}: ${trace}" \
    -X POST "${API_URL}/customers" \
    -d "${payload}" | jq
}

update_customer() {
  local customer_id trace payload
  customer_id="${1:?Укажите идентификатор покупателя}"
  trace="$(trace_id)"
  payload=$(cat <<JSON
{
  "email": "updated@example.com",
  "phone": "+10987654321",
  "segments": ["electronics", "vip", "loyal"],
  "attributes": {"preferred_channel": "sms", "lifetime_value": "platinum"}
}
JSON
)

  curl -sS -H "Content-Type: application/json" -H "${TRACE_ID_HEADER}: ${trace}" \
    -X PUT "${API_URL}/customer/${customer_id}" \
    -d "${payload}" | jq
}

case "${1:-}" in
  create)
    create_customer "${2:-}"
    ;;
  update)
    update_customer "${2:?Укажите идентификатор покупателя для обновления}"
    ;;
  *)
    cat <<'HELP'
Использование:
  ./customers.sh create [CUSTOMER_ID]  # создать покупателя
  ./customers.sh update CUSTOMER_ID   # обновить покупателя

Переменные окружения:
  API_URL - адрес сервиса (по умолчанию http://localhost:9090)
HELP
    ;;
esac


