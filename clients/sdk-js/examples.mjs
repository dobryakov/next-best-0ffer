import { randomUUID } from 'node:crypto';
import { createNboClient } from './index.js';

const client = createNboClient();
const customerId = randomUUID();

async function main() {
  console.log('Создаю покупателя…');
  await client.createCustomer({
    id: customerId,
    email: 'js-sdk@example.com',
    segments: ['js', 'beta'],
    attributes: { source: 'sdk-js' },
  });

  console.log('Отправляю событие…');
  await client.sendEvent({
    idempotency_token: randomUUID(),
    category: 'view',
    customer_id: customerId,
    product_ids: ['SKU-001'],
    channel: 'web',
    occurred_at: new Date().toISOString(),
    payload: { source: 'sdk-js' },
  });

  console.log('Запрашиваю рекомендации…');
  const recommendation = await client.getRecommendation(customerId, {
    channel: 'web',
    variant: 'control',
  });

  console.log(JSON.stringify(recommendation, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

