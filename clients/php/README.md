# PHP клиент для Next Best Offer API

Минимальная CLI-утилита без зависимостей (использует `curl` расширение PHP).

## Требования

- PHP 8.1+ с включённым расширением `curl`
- Доступ к запущенному API (см. `../../specs/001-define-nbo-api/quickstart.md`)

## Установка

```bash
cd clients/php
chmod +x cli.php         # уже выполнено в репозитории, повторите при необходимости
```

## Использование

```bash
# создать покупателя
php cli.php customers:create

# обновить покупателя
php cli.php customers:update 11111111-1111-1111-1111-111111111111

# отправить событие
php cli.php events:send 11111111-1111-1111-1111-111111111111 SKU-001 view web

# запросить NBO
php cli.php nbo:get 11111111-1111-1111-1111-111111111111 web control
```

Переменная `API_URL` позволяет переопределить адрес сервиса:

```bash
API_URL=http://api:9090 php cli.php nbo:get 1111-...
```

Вывод форматируется в JSON для удобства обработки в скриптах/pipe:

```bash
php cli.php nbo:get ... | jq '.offers'
```

