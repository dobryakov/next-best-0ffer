# JS SDK для Next Best Offer API

Минимальный набор helper-функций на Node.js 18+ без сторонних зависимостей.

## Установка

```bash
cd clients/sdk-js
npm install   # зависимостей нет, но команда подготовит lock-файл при необходимости
```

## Использование

```js
import { createNboClient } from './index.js';

const client = createNboClient({ baseUrl: 'http://localhost:9090' });
const customerId = crypto.randomUUID();

await client.createCustomer({ id: customerId, segments: ['vip'] });
await client.sendEvent({
  idempotency_token: crypto.randomUUID(),
  category: 'view',
  customer_id: customerId,
  product_ids: ['SKU-001'],
  channel: 'web',
  occurred_at: new Date().toISOString(),
});

const response = await client.getRecommendation(customerId, { channel: 'web' });
console.log(response);
```

Готовый пример:

```bash
npm run example
```

Переменная окружения `API_URL` позволяет переопределить адрес сервиса.

