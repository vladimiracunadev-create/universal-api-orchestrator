# Solo lectura. Definir $env:GATEWAY_API_KEY en la sesión, sin guardar el secreto en este archivo.
$ErrorActionPreference = "Stop"
if (-not $env:GATEWAY_API_KEY) { throw "Falta GATEWAY_API_KEY" }
$base = if ($env:GATEWAY_URL) { $env:GATEWAY_URL } else { "http://127.0.0.1:8080" }
$payload = @{ system="gmail"; operation="list_messages"; params=@{ q="is:unread"; maxResults=5 } } | ConvertTo-Json -Depth 10
$result = Invoke-RestMethod -Uri "$base/v1/execute" -Method Post -ContentType "application/json; charset=utf-8" -Headers @{ "X-API-Key"=$env:GATEWAY_API_KEY } -Body $payload -TimeoutSec 60
$result | ConvertTo-Json -Depth 30
if (-not $result.ok) { exit 2 }
