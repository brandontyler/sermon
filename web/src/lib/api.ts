import { resolveTenant } from "./tenant";

/** API base URL — empty in production (same-origin through SWA proxy) */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Fetch wrapper that adds x-tenant header when on a church subdomain. */
export function tenantFetch(url: string, init?: RequestInit): Promise<Response> {
  const tenant = resolveTenant();
  if (!tenant) return fetch(url, init);
  const headers = new Headers(init?.headers);
  headers.set("x-tenant", tenant.id);
  return fetch(url, { ...init, headers });
}

/** Fetch wrapper for admin endpoints. SWA proxy injects x-ms-client-principal server-side. */
export async function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), init);
}
