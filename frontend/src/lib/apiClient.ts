/**
 * Centralized API client for QPilot frontend.
 * Base URL is sourced from NEXT_PUBLIC_API_BASE_URL (.env.local).
 * All routes STRICTLY follow FRONTEND_INTEGRATION_GUIDE.md.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface FetchOptions extends RequestInit {
  json?: unknown;
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { json, headers, ...rest } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(headers as Record<string, string>),
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
    ...rest,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`[${response.status}] ${text}`);
  }

  return response.json() as Promise<T>;
}
