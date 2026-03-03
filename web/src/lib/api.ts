/** API base URL — Function App direct (SWA Free tier doesn't support linked backends) */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
