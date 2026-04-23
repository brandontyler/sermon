"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { resolveTenant } from "@/lib/tenant";

/** Action cards — only shown on the main site, hidden on tenant subdomains. */
export default function ActionButtons() {
  const [isTenant, setIsTenant] = useState(false);

  useEffect(() => {
    setIsTenant(!!resolveTenant());
  }, []);

  if (isTenant) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
      <Link
        href="/upload"
        style={{ border: "1px solid #e5e7eb", background: "#ffffff" }}
        className="group block rounded-lg p-8 text-center hover:border-[#2563eb] hover:shadow-md transition-all"
      >
        <div className="text-4xl mb-4">🎙️</div>
        <h2 className="text-lg font-semibold text-[#111827] mb-2">Upload a Sermon</h2>
        <p className="text-sm text-[#6b7280] mb-4">Audio, text, or YouTube — get your sermon scored</p>
        <span className="text-sm font-medium text-[#2563eb] group-hover:underline">Get started →</span>
      </Link>

      <Link
        href="/sermons"
        style={{ border: "1px solid #e5e7eb", background: "#ffffff" }}
        className="group block rounded-lg p-8 text-center hover:border-[#2563eb] hover:shadow-md transition-all"
      >
        <div className="text-4xl mb-4">📊</div>
        <h2 className="text-lg font-semibold text-[#111827] mb-2">Browse Sermons</h2>
        <p className="text-sm text-[#6b7280] mb-4">Scores, trends, and detailed breakdowns</p>
        <span className="text-sm font-medium text-[#2563eb] group-hover:underline">View sermons →</span>
      </Link>

    </div>
  );
}
