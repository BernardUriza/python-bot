import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for Azure Static Web Apps: the API is the only server
  // process; the front is a static bundle that calls it.
  output: "export",
  reactStrictMode: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compress: true,
  typedRoutes: true,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  // The Image optimizer needs a server; static export can't run it.
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
