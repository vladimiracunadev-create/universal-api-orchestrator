<?php
/** Cliente PHP backend (PHP 8+, extensión cURL). No expone credenciales al frontend. */
declare(strict_types=1);
$key = getenv('GATEWAY_API_KEY');
if (!$key) { throw new RuntimeException('Defina GATEWAY_API_KEY en el entorno del proceso PHP.'); }
$base = rtrim(getenv('GATEWAY_URL') ?: 'http://127.0.0.1:8080', '/');
$handle = curl_init($base . '/v1/execute');
curl_setopt_array($handle, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT => 60,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'X-API-Key: ' . $key],
    CURLOPT_POSTFIELDS => json_encode([
        'system' => 'gmail', 'operation' => 'list_messages',
        'params' => ['q' => 'is:unread', 'maxResults' => 5],
    ], JSON_THROW_ON_ERROR),
]);
$body = curl_exec($handle);
$status = curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
curl_close($handle);
if ($body === false || $status < 200 || $status >= 300) {
    throw new RuntimeException('Fallo de conexión o autorización en el gateway.');
}
$result = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR) . PHP_EOL;
exit(($result['ok'] ?? false) ? 0 : 2);
