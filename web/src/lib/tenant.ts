/** Tenant resolution from hostname. */

export interface Tenant {
  id: string;
  name: string;
}

/** Map of subdomain → tenant id. */
const SUBDOMAIN_MAP: Record<string, string> = {
  dentonbible: "denton-bible",
};

/**
 * Resolve tenant from window.location.hostname.
 * Returns null on the public site (howwas.church, localhost, etc.).
 */
export function resolveTenant(): Tenant | null {
  if (typeof window === "undefined") return null;
  const host = window.location.hostname;

  // Local dev: check for tenant query param
  if (host === "localhost" || host === "127.0.0.1") {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tenant");
    if (t) return { id: t, name: t };
    return null;
  }

  // Production: extract subdomain from *.howwas.church
  const match = host.match(/^([^.]+)\.howwas\.church$/);
  if (!match || match[1] === "www") return null;

  const sub = match[1];
  const id = SUBDOMAIN_MAP[sub] || sub;
  return { id, name: sub };
}
