// Cliente backend Node.js con fetch. Nunca incluir claves en JavaScript servido al navegador.
// Ejemplo: node --env-file=.env examples/clients/node_client.mjs (Node con soporte --env-file).
const key = process.env.GATEWAY_API_KEY;
if (!key) throw new Error("Falta GATEWAY_API_KEY");
try {
  const response = await fetch(`${process.env.GATEWAY_URL ?? "http://127.0.0.1:8080"}/v1/execute`, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-API-Key": key},
    body: JSON.stringify({system: "gmail", operation: "list_messages", params: {q: "is:unread", maxResults: 5}}),
    signal: AbortSignal.timeout(60000),
    redirect: "error",
  });
  if (!response.ok) throw new Error(`Gateway HTTP ${response.status}`);
  const result = await response.json();
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 2;
} catch (error) {
  console.error("No se pudo completar la consulta al gateway.");
  process.exitCode = 1;
}
