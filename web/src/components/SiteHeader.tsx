"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function SiteHeader() {
  const pathname = usePathname();

  function navClass(href: string) {
    const active = pathname === href || (href !== "/" && pathname?.startsWith(href));
    return `px-3 py-2 text-sm transition-colors ${active ? "text-[#2563eb] font-medium" : "text-[#374151] hover:text-[#2563eb]"}`;
  }

  return (
    <nav style={{ borderBottom: "1px solid #e5e7eb", background: "#ffffff" }} className="px-6 py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 via-orange-500 to-red-500 flex items-center justify-center text-base font-bold text-white">
            P
          </div>
          <Link href="/" className="text-lg font-semibold text-[#111827] hover:text-[#2563eb] transition-colors">
            PSR
          </Link>
          <span className="text-sm text-[#6b7280] hidden sm:inline">Pastor Sermon Rating</span>
        </div>
        <div className="flex items-center gap-1">
          <Link href="/sermons" className={navClass("/sermons")}>Sermons</Link>
          <Link href="/dashboard" className={navClass("/dashboard")}>Dashboard</Link>
          <Link href="/support" className={navClass("/support")}>Support</Link>
          <Link
            href="/upload"
            className="ml-3 px-4 py-2 text-sm font-medium bg-[#2563eb] text-white rounded hover:bg-[#1d4ed8] transition-colors"
          >
            Upload a Sermon
          </Link>
        </div>
      </div>
    </nav>
  );
}
