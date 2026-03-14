"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Upload" },
  { href: "/sermons", label: "Sermons" },
  { href: "/churches", label: "Churches" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function NavBar() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-[1200px] mx-auto px-4 h-14 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-baseline gap-2 shrink-0">
          <span className="text-base font-bold text-gray-900 tracking-tight">PSR</span>
          <span className="text-xs text-gray-400 hidden sm:inline">Pastor Sermon Rating</span>
        </Link>

        {/* Primary nav */}
        <nav className="flex items-center gap-1" aria-label="Main navigation">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                isActive(href)
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              }`}
              aria-current={isActive(href) ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
          <Link
            href="/admin"
            className={`ml-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              isActive("/admin")
                ? "bg-gray-100 text-gray-600"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
            }`}
            aria-current={isActive("/admin") ? "page" : undefined}
          >
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
}
