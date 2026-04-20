"use client";

import { useEffect, useState } from "react";

export default function AdminGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"loading" | "authorized" | "unauthorized">("loading");

  useEffect(() => {
    fetch("/.auth/me")
      .then(r => r.json())
      .then(d => setState(d.clientPrincipal ? "authorized" : "unauthorized"))
      .catch(() => setState("unauthorized"));
  }, []);

  if (state === "loading") return <div className="max-w-[960px] mx-auto p-4 py-8 text-gray-400 text-sm">Checking authorization...</div>;
  if (state === "unauthorized") return (
    <div className="max-w-[960px] mx-auto p-4 py-8 text-center">
      <p className="text-red-600 font-medium mb-4">Unauthorized</p>
      <a href="/.auth/login/aad?post_login_redirect_uri=.referrer" className="text-sm text-blue-600 hover:underline">Sign in with Microsoft</a>
    </div>
  );
  return <>{children}</>;
}
