"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { resolveTenant } from "@/lib/tenant";

/** Shows a menu row on tenant subdomains (below PSR branding). */
export default function TenantMenu() {
  const [isTenant, setIsTenant] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setIsTenant(!!resolveTenant());
    fetch("/.auth/me")
      .then((r) => r.json())
      .then((d) => { if (d?.clientPrincipal) setLoggedIn(true); })
      .catch(() => {});
  }, []);

  if (!isTenant) return null;

  return (
    <nav className="flex flex-wrap justify-center gap-3 mb-8 mt-2">
      {loggedIn ? (
        <Link href="/account" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">Account</Link>
      ) : (
        <Link href="/.auth/login/aad?post_login_redirect_uri=/account" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">Sign In</Link>
      )}
      <Link href="/" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">PSR</Link>
      <Link href="/samples" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">Samples</Link>
      <Link href="/support" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">Support</Link>
      <a href="/contact" className="px-4 py-2 text-sm font-medium rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors">Contact Us</a>
    </nav>
  );
}
