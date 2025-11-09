#!/usr/bin/env bash

# Получение Next Best Offer с polling-режимом.

set -euo pipefail

API_URL="${API_URL:-http://localhost:9090}"
TRACE_HEADER="X-Trace-Id"

trace_id() {
  tr -d '\n' < /proc/sys/kernel/random/uuid
}

usage() {
  cat <<'HELP'
Использование:
  ./nbo.sh get CUSTOMER_ID [CHANNEL] [VARIANT] [RETRIES] [SLEEP]

Параметры:
  CUSTOMER_ID  UUID покупателя
  CHANNEL      Канал (по умолчанию web)
  VARIANT      Вариант эксперимента (по умолчанию control)
  RETRIES      Количество повторов при статусе 202 (по умолчанию 0)
  SLEEP        Пауза между повторами, секунды (по умолчанию 5)

Пример:
  ./nbo.sh get 1111-... web treatmentA 3 10
HELP
}

get_nbo() {
  local customer_id="${1:?Укажите CUSTOMER_ID}"
  local channel="${2:-web}"
  local variant="${3:-control}"
  local retries="${4:-0}"
  local sleep_seconds="${5:-5}"
  local attempt=0

  while true; do
    attempt=$((attempt + 1))
    response=$(curl -sS -w '\n%{http_code}' \
      -H "${TRACE_HEADER}: $(trace_id)" \
      -G "${API_URL}/nbo/${customer_id}" \
      --data-urlencode "channel=${channel}" \
      --data-urlencode "variant=${variant}")

    http_code=$(echo "${response}" | tail -n1)
    body=$(echo "${response}" | sed '$d')

    echo "Запрос #${attempt}, HTTP ${http_code}"
    echo "${body}" | jq

    if [[ "${http_code}" -eq 200 || "${http_code}" -eq 404 ]]; then
      return 0
    fi

    if [[ "${http_code}" -eq 202 && "${attempt}" -le $((retries + 1)) ]]; then
      echo "Ожидание ${sleep_seconds}s перед повторным запросом..."
      sleep "${sleep_seconds}"
      continue
    fi

    echo "Получен неожиданный статус ${http_code}" >&2
    return 1
  done
}

case "${1:-}" in
  get)
    shift
    get_nbo "$@"
    ;;
  *)
    usage
    ;;
esac

