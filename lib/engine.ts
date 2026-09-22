/**
 * Calls into the Python engine.
 *
 * Deployed on Vercel, the engine is the Python function at /api/engine on the
 * same origin. Locally, Next.js cannot run Python, so NEXT_PUBLIC_ENGINE_URL
 * points at scripts/engine_server.py instead.
 */
const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || "/api/engine";

export async function engine<T = Record<string, unknown>>(
  body: Record<string, unknown>
): Promise<T> {
  const response = await fetch(ENGINE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || (payload as { error?: string }).error) {
    throw new Error(
      (payload as { error?: string }).error ??
        `The engine answered ${response.status}.`
    );
  }
  return payload as T;
}
