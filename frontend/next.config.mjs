/** @type {import('next').NextConfig} */

// GitHub Pages serves project sites from a sub-path
// (e.g. /Blockchain-Honeypot-Detection), so the base path is configurable at
// build time. When unset (local dev, Docker) the app is served from "/".
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig = {
  reactStrictMode: true,
  // Static export so the dashboard can be hosted on GitHub Pages with no server.
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
  },
};

export default nextConfig;
