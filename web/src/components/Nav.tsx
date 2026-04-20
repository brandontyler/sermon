"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/sermons", label: "Sermons" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
];

const MORE_LINKS = [
  { href: "/churches", label: "Churches" },
  { href: "/calculations", label: "Calculations" },
];

const ADMIN_LINKS = [
  { href: "/admin/manage", label: "Manage" },
  { href: "/admin/feeds", label: "Feeds" },
  { href: "/admin", label: "Bonus" },
  { href: "/church-admin", label: "Churches" },
];

export default function Nav() {
  const pathname = usePathname();
  const isAdmin = pathname?.startsWith("/admin") || pathname === "/church-admin";
  const [open, setOpen] = useState(false);

  function isActive(href: string) {
    if (href === "/admin") return pathname === "/admin";
    return pathname === href || pathname?.startsWith(href + "/");
  }

  const primary = isAdmin ? ADMIN_LINKS : LINKS;
  const secondary = isAdmin ? [{ href: "/sermons", label: "← Sermons" }] : [...MORE_LINKS, { href: "/admin/manage", label: "Admin" }];

  return (
    <nav className="relative text-sm mb-8">
      <div className="flex items-baseline gap-4">
        <Link href="/" className="font-semibold text-gray-900 hover:text-gray-700 mr-1">PSR</Link>
        {primary.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={isActive(href)
              ? "text-gray-900 font-medium"
              : "text-gray-400 hover:text-gray-600"}
          >
            {label}
          </Link>
        ))}
        <button
          onClick={() => setOpen(!open)}
          className="text-gray-300 hover:text-gray-500 ml-auto"
          aria-label="More pages"
        >
          ···
        </button>
      </div>
      {open && (
        <div className="absolute right-0 top-7 bg-white border border-gray-200 rounded-lg shadow-sm py-1 z-50">
          {secondary.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 whitespace-nowrap"
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
