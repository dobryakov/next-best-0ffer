#!/usr/bin/env bash

# Пример регистрации событий в Next Best Offer API.

set -euo pipefail

API_URL="${API_URL:-http://localhost:9090}"
TRACE_HEADER="X-Trace-Id"

trace_id() {
  tr -d '\n' < /proc/sys/kernel/random/uuid
}

usage() {
  cat <<'HELP'
Использование:
  ./events.sh send CUSTOMER_ID PRODUCT_ID [CATEGORY] [CHANNEL]

Параметры:
  CUSTOMER_ID  UUID покупателя (должен существовать в системе)
  PRODUCT_ID   SKU товара
  CATEGORY     Категория события (view, search, add_to_cart, purchase). По умолчанию: view
  CHANNEL      Канал взаимодействия (web, mobile, pos). По умолчанию: web

Переменные окружения:
  API_URL      URL сервиса API (по умолчанию http://localhost:9090)

Примеры:
  ./events.sh send 1111-... SKU-001
  ./events.sh send 1111-... SKU-001 purchase mobile
HELP
}

send_event() {
  local customer_id="${1:?Укажите CUSTOMER_ID}"
  local product_id="${2:?Укажите PRODUCT_ID}"
  local category="${3:-view}"
  local channel="${4:-web}"
  local payload trace response

  trace="$(trace_id)"
  payload=$(cat <<JSON
{
  "idempotency_token": "$(trace_id)",
  "category": "${category}",
  "customer_id": "${customer_id}",
  "product_ids": ["${product_id}"],
  "channel": "${channel}",
  "occurred_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "payload": {"source": "cli"}
}
JSON
)

  response=$(curl -sS -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -H "${TRACE_HEADER}: ${trace}" \
    -X POST "${API_URL}/events" \
    -d "${payload}")

  http_code=$(echo "${response}" | tail -n1)
  body=$(echo "${response}" | sed '$d')

  if [[ "${http_code}" -ne 202 ]]; then
    echo "Ошибка: HTTP ${http_code}" >&2
    echo "${body}" >&2
    exit 1
  fi

  echo "${body}" | jq
}

case "${1:-}" in
  send)
    shift
    send_event "$@"
    ;;
  *)
    usage
    ;;
esac

