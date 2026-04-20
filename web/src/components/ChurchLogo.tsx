"use client";

import { useEffect, useState } from "react";
import { resolveTenant } from "@/lib/tenant";
import { getTheme, ThemeColors } from "@/lib/themes";

/** Renders the church logo above PSR branding when on a themed subdomain. */
export default function ChurchLogo() {
  const [theme, setTheme] = useState<ThemeColors | null>(null);

  useEffect(() => {
    const t = resolveTenant();
    if (t) setTheme(getTheme(t.id));
  }, []);

  if (!theme?.logoUrl) return null;

  return (
    <div className="mb-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={theme.logoUrl} alt={theme.logoAlt ?? ""} className="h-16 mx-auto" />
    </div>
  );
}
