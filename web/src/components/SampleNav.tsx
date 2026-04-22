"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function SampleNav() {
  const pathname = usePathname();
  const isDashboard = pathname === "/samples/dashboard" || pathname === "/dashboard";
  const isSermon = !isDashboard;

  return (
    <div className="flex gap-2 mb-6">
      <Link
        href="/samples"
        className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${isSermon ? "bg-blue-600 text-white border-blue-600" : "bg-white/10 border-white/20 hover:bg-white/20"}`}
      >
        Sermon
      </Link>
      <Link
        href="/samples/dashboard"
        className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${isDashboard ? "bg-blue-600 text-white border-blue-600" : "bg-white/10 border-white/20 hover:bg-white/20"}`}
      >
        Dashboard
      </Link>
    </div>
  );
}
