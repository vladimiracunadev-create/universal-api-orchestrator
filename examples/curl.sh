#!/usr/bin/env bash
set -euo pipefail
: "${GATEWAY_API_KEY:?Exporta GATEWAY_API_KEY antes de ejecutar este cliente}"
curl --fail-with-body --max-time 60 -X POST http://127.0.0.1:8080/v1/execute   -H "X-API-Key: ${GATEWAY_API_KEY}"   -H 'Content-Type: application/json'   --data @examples/requests/gmail-search.json
