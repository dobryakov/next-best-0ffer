#!/usr/bin/env php
<?php
declare(strict_types=1);

/**
 * Простая CLI-утилита для работы с Next Best Offer API.
 *
 * Примеры:
 *   php cli.php customers:create 11111111-1111-1111-1111-111111111111
 *   php cli.php events:send 1111-... SKU-001 view web
 *   php cli.php nbo:get 1111-...
 */

$apiUrl = rtrim(getenv('API_URL') ?: 'http://localhost:9090', '/');

$commands = $argv;
array_shift($commands);

if (count($commands) === 0) {
    usage();
    exit(0);
}

$command = array_shift($commands);

try {
    switch ($command) {
        case 'customers:create':
            $customerId = $commands[0] ?? uuidv4();
            $response = post('/customers', [
                'id' => $customerId,
                'email' => 'php-client@example.com',
                'phone' => '+79990000000',
                'name' => 'PHP Customer',
                'segments' => ['php', 'vip'],
                'attributes' => ['source' => 'php-cli'],
            ]);
            output($response);
            break;
        case 'customers:update':
            $customerId = $commands[0] ?? null;
            if ($customerId === null) {
                throw new InvalidArgumentException('Укажите идентификатор покупателя.');
            }
            $response = put("/customer/{$customerId}", [
                'email' => 'php-client-updated@example.com',
                'segments' => ['php', 'loyal'],
                'attributes' => ['source' => 'php-cli', 'tier' => 'gold'],
            ]);
            output($response);
            break;
        case 'events:send':
            $customerId = $commands[0] ?? null;
            $productId = $commands[1] ?? null;
            $category = $commands[2] ?? 'view';
            $channel = $commands[3] ?? 'web';
            if ($customerId === null || $productId === null) {
                throw new InvalidArgumentException('Синтаксис: events:send CUSTOMER_ID PRODUCT_ID [CATEGORY] [CHANNEL]');
            }
            $response = post('/events', [
                'idempotency_token' => uuidv4(),
                'category' => $category,
                'customer_id' => $customerId,
                'product_ids' => [$productId],
                'channel' => $channel,
                'occurred_at' => (new DateTimeImmutable('now', new DateTimeZone('UTC')))->format(DateTimeInterface::ATOM),
                'payload' => ['source' => 'php-cli'],
            ]);
            output($response);
            break;
        case 'nbo:get':
            $customerId = $commands[0] ?? null;
            $channel = $commands[1] ?? 'web';
            $variant = $commands[2] ?? 'control';
            if ($customerId === null) {
                throw new InvalidArgumentException('Синтаксис: nbo:get CUSTOMER_ID [CHANNEL] [VARIANT]');
            }
            $response = get("/nbo/{$customerId}", [
                'channel' => $channel,
                'variant' => $variant,
            ]);
            output($response);
            break;
        default:
            usage();
    }
} catch (Throwable $exception) {
    fwrite(STDERR, "Ошибка: {$exception->getMessage()}\n");
    exit(1);
}

function usage(): void
{
    echo <<<HELP
Доступные команды:
  php cli.php customers:create [CUSTOMER_ID]
  php cli.php customers:update CUSTOMER_ID
  php cli.php events:send CUSTOMER_ID PRODUCT_ID [CATEGORY] [CHANNEL]
  php cli.php nbo:get CUSTOMER_ID [CHANNEL] [VARIANT]

Переменные окружения:
  API_URL  Базовый адрес сервиса (по умолчанию http://localhost:9090)

HELP;
}

function get(string $path, array $query = []): array
{
    $url = buildUrl($path, $query);
    return request('GET', $url, null);
}

function post(string $path, array $payload): array
{
    $url = buildUrl($path);
    return request('POST', $url, $payload);
}

function put(string $path, array $payload): array
{
    $url = buildUrl($path);
    return request('PUT', $url, $payload);
}

function buildUrl(string $path, array $query = []): string
{
    global $apiUrl;
    $url = $apiUrl . $path;
    if ($query !== []) {
        $url .= '?' . http_build_query($query);
    }
    return $url;
}

function request(string $method, string $url, ?array $payload): array
{
    $ch = curl_init($url);
    $headers = [
        'Accept: application/json',
        'X-Trace-Id: ' . uuidv4(),
    ];
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => 15,
    ]);

    if ($payload !== null) {
        $json = json_encode($payload, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
        $headers[] = 'Content-Type: application/json';
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $json);
    }

    $response = curl_exec($ch);
    if ($response === false) {
        throw new RuntimeException('Сетевой запрос не удался: ' . curl_error($ch));
    }

    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $decoded = json_decode($response, true);
    if ($decoded === null && json_last_error() !== JSON_ERROR_NONE) {
        throw new RuntimeException('Ответ не является корректным JSON.');
    }

    if ($status >= 400) {
        throw new RuntimeException(sprintf('HTTP %d: %s', $status, $response));
    }

    return $decoded ?? [];
}

function output(array $payload): void
{
    echo json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . PHP_EOL;
}

function uuidv4(): string
{
    $data = random_bytes(16);
    $data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
    $data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}

