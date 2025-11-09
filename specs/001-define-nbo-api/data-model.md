# Data Model — Next Best Offer API

## 1. Покупатель (`customers`)

| Поле | Тип | Обязательность | Описание | Валидация / Примечания |
|------|-----|----------------|----------|------------------------|
| `id` | UUID | required | Уникальный идентификатор покупателя | Проверка на UUIDv4, уникальный индекс |
| `email` | string | optional | Email для коммуникаций | RFC 5322 формат, uniqueness partial index |
| `phone` | string | optional | Номер телефона | E.164 формат |
| `name` | string | optional | Имя и фамилия | 1–200 символов |
| `segments` | array<string> | optional | Маркетинговые сегменты | Значения из справочника, max 20 сегментов |
| `attributes` | jsonb | optional | Пользовательские атрибуты | Ограничение по размеру 16 KB |
| `created_at` | timestamp | required | Время создания записи | Дефолт на стороне БД |
| `updated_at` | timestamp | required | Время последнего обновления | Автообновление триггером |

### State Transitions
- `new` → `active` при первом создании.
- `active` → `suppressed` при явном флаге в атрибутах (например, GDPR удаление).

## 2. Продукт (`products`)

| Поле | Тип | Обязательность | Описание | Валидация / Примечания |
|------|-----|----------------|----------|------------------------|
| `id` | string | required | SKU/артикул | Уникальный индекс, max 64 символа |
| `title` | string | required | Название | 1–255 символов |
| `category` | string | required | Категория каталога | Справочник категорий |
| `price` | decimal(12,2) | required | Цена | ≥ 0, поддержка валюты в атрибутах |
| `availability` | jsonb | required | Наличие по каналам | Структура `{channel: bool}` |
| `attributes` | jsonb | optional | Дополнительные свойства | Ограничение 32 KB |
| `updated_at` | timestamp | required | Время последнего обновления | Автообновление |

## 3. Событие (`events`)

| Поле | Тип | Обязательность | Описание | Валидация / Примечания |
|------|-----|----------------|----------|------------------------|
| `id` | UUID | required | Идентификатор события (генерируется API) | Значение детерминировано (hash payload + timestamp) |
| `category` | enum | required | `view`, `search`, `add_to_cart`, `purchase` | Ограничение CHECK |
| `customer_id` | UUID | required | Ссылка на покупателя | FK → customers(id) |
| `product_ids` | array<string> | optional | Список SKU | Не пустой для всех категорий, кроме `search` |
| `channel` | string | required | Канал продаж | Справочник каналов |
| `occurred_at` | timestamp | required | Время действия пользователя | Проверка на разумный диапазон (±7 дней) |
| `payload` | jsonb | optional | Дополнительные данные | Ограничение 16 KB |
| `ingested_at` | timestamp | required | Время приёма системой | Автоустановка |

### Idempotency
- При повторном событии с теми же `customer_id`, `category`, `product_ids`, `channel`, `occurred_at`, `payload` в пределах 10 минут генерируется тот же `id`.

## 4. Рекомендация (`recommendations`)

| Поле | Тип | Обязательность | Описание | Валидация / Примечания |
|------|-----|----------------|----------|------------------------|
| `id` | UUID | required | Идентификатор расчёта | Генерируется воркером |
| `customer_id` | UUID | required | Ссылка на покупателя | FK → customers(id) |
| `status` | enum | required | `pending`, `ready`, `failed` | CHECK |
| `offers` | array<jsonb> | optional | Список объектов `{product_id, score, reason}` | До 10 элементов |
| `generated_at` | timestamp | optional | Время завершения расчёта | Null в `pending` |
| `retry_after` | timestamp | optional | Когда повторить запрос | Используется при `pending` |
| `metadata` | jsonb | optional | Доп. данные (модель, версия, канал) | 16 KB |

## Связи

- `events.customer_id` → `customers.id`
- `recommendations.customer_id` → `customers.id`
- Мягкая связь `offers.product_id` → `products.id` (валидация на уровне приложения)

## Feature Store Слои

- **Customer Features**: RFM (recency, frequency, monetary), средний чек, разнообразие категорий, последняя активность.
- **Product Features**: Категория, цена, маржинальность, популярность, сезонность.
- **Interaction Features**: Частота взаимодействий покупатель × SKU, время с последней покупки, канал первого контакта.

## Очереди и состояние воркеров

- Очередь `nbo_calculation` в Redis: задача содержит `customer_id`, snapshot признаков, SLA 30 секунд.
- Таблица контроля `calculation_jobs` хранит статус и ссылки на воркер.

