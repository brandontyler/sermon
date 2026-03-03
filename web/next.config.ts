import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // SWA handles /api/* routing via linked backend
};

export default nextConfig;
