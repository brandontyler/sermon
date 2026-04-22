"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { resolveTenant } from "@/lib/tenant";

/** Big action buttons — only shown on the main site, hidden on tenant subdomains. */
export default function ActionButtons() {
  const [isTenant, setIsTenant] = useState(false);

  useEffect(() => {
    setIsTenant(!!resolveTenant());
  }, []);

  if (isTenant) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full max-w-[720px]">
      <Link href="/upload" className="theme-card theme-card-1 group relative rounded-2xl p-8 text-center transition-all duration-300 hover:scale-105 hover:-translate-y-1 bg-white/10 backdrop-blur-md border">
        <div className="text-4xl mb-4">🎙️</div>
        <h2 className="text-xl font-bold mb-2">Upload</h2>
        <p className="text-sm theme-muted">Audio, text, or YouTube — get your sermon scored</p>
      </Link>

      <Link href="/sermons" className="theme-card theme-card-2 group relative rounded-2xl p-8 text-center transition-all duration-300 hover:scale-105 hover:-translate-y-1 bg-white/10 backdrop-blur-md border">
        <div className="text-4xl mb-4">📊</div>
        <h2 className="text-xl font-bold mb-2">Sermons</h2>
        <p className="text-sm theme-muted">Browse scores, trends, and detailed breakdowns</p>
      </Link>

      <Link href="/churches" className="theme-card theme-card-3 group relative rounded-2xl p-8 text-center transition-all duration-300 hover:scale-105 hover:-translate-y-1 bg-white/10 backdrop-blur-md border">
        <div className="text-4xl mb-4">⛪</div>
        <h2 className="text-xl font-bold mb-2">Find a Church</h2>
        <p className="text-sm theme-muted">Discover churches and their pastors</p>
      </Link>
    </div>
  );
}
