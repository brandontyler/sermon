"use client";

import { useEffect } from "react";
import { resolveTenant } from "@/lib/tenant";
import { getTheme } from "@/lib/themes";

/** Applies per-tenant CSS custom properties + data-theme attribute to <html>. */
export default function ThemeProvider() {
  useEffect(() => {
    const tenant = resolveTenant();
    if (!tenant) return;
    const theme = getTheme(tenant.id);
    if (!theme) return;

    const root = document.documentElement;
    root.setAttribute("data-theme", tenant.id);
    root.style.setProperty("--bg-gradient", theme.bgGradient);
    root.style.setProperty("--accent", theme.accent);
    root.style.setProperty("--accent-hover", theme.accentHover);
    root.style.setProperty("--muted-accent", theme.mutedAccent);
    root.style.setProperty("--muted-accent-faint", theme.mutedAccentFaint);
    root.style.setProperty("--card-bg", theme.cardBg);
    root.style.setProperty("--card-border", theme.cardBorder);
    root.style.setProperty("--orb1", theme.orb1);
    root.style.setProperty("--orb2", theme.orb2);
    root.style.setProperty("--orb3", theme.orb3);
    root.style.setProperty("--shadow1", theme.shadow1);
    root.style.setProperty("--shadow1-hover", theme.shadow1Hover);
    root.style.setProperty("--shadow2", theme.shadow2);
    root.style.setProperty("--shadow2-hover", theme.shadow2Hover);
    root.style.setProperty("--shadow3", theme.shadow3);
    root.style.setProperty("--shadow3-hover", theme.shadow3Hover);

    return () => {
      root.removeAttribute("data-theme");
      root.style.removeProperty("--bg-gradient");
    };
  }, []);

  return null;
}
