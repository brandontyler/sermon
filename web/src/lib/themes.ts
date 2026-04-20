/** Per-tenant theme overrides applied as CSS custom properties. */

export interface ThemeColors {
  /** Body background gradient */
  bgGradient: string;
  /** Accent color for buttons, links */
  accent: string;
  accentHover: string;
  /** Muted text accent (replaces indigo-300 etc.) */
  mutedAccent: string;
  mutedAccentFaint: string;
  /** Card/glass background */
  cardBg: string;
  cardBorder: string;
  /** Orb colors (home page animated blobs) */
  orb1: string;
  orb2: string;
  orb3: string;
  /** Shadow accent for home cards */
  shadow1: string;
  shadow1Hover: string;
  shadow2: string;
  shadow2Hover: string;
  shadow3: string;
  shadow3Hover: string;
  /** Optional church logo URL shown on home page */
  logoUrl?: string;
  logoAlt?: string;
}

const themes: Record<string, ThemeColors> = {
  "denton-bible": {
    bgGradient: "linear-gradient(135deg, #092e4a, #101421, #092e4a)",
    accent: "#317ff3",
    accentHover: "#5a9af5",
    mutedAccent: "#8ab4d6",
    mutedAccentFaint: "rgba(138,180,214,0.7)",
    cardBg: "rgba(255,255,255,0.08)",
    cardBorder: "rgba(138,180,214,0.2)",
    orb1: "rgba(54,119,159,0.25)",
    orb2: "rgba(49,127,243,0.2)",
    orb3: "rgba(114,130,99,0.2)",
    shadow1: "rgba(49,127,243,0.4)",
    shadow1Hover: "rgba(49,127,243,0.55)",
    shadow2: "rgba(114,130,99,0.4)",
    shadow2Hover: "rgba(114,130,99,0.55)",
    shadow3: "rgba(54,119,159,0.4)",
    shadow3Hover: "rgba(54,119,159,0.55)",
    logoUrl: "https://dentonbible.org/_assets/img/logos/logo-white.svg",
    logoAlt: "Denton Bible Church",
  },
};

export function getTheme(tenantId: string): ThemeColors | null {
  return themes[tenantId] ?? null;
}
