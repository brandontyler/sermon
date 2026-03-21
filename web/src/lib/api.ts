/** API base URL — Function App direct (SWA Free tier doesn't support linked backends) */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Cached client principal from SWA /.auth/me */
let _principalCache: string | null = null;

async function getClientPrincipal(): Promise<string | null> {
  if (_principalCache) return _principalCache;
  try {
    const r = await fetch("/.auth/me");
    if (!r.ok) return null;
    const { clientPrincipal } = await r.json();
    if (!clientPrincipal) return null;
    _principalCache = btoa(JSON.stringify(clientPrincipal));
    return _principalCache;
  } catch {
    return null;
  }
}

/** Fetch wrapper that forwards SWA auth to the Function App */
export async function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const principal = await getClientPrincipal();
  const headers = new Headers(init?.headers);
  if (principal) headers.set("x-ms-client-principal", principal);
  return fetch(apiUrl(path), { ...init, headers });
}
