import type { NextConfig } from "next";

/** Multipart payloads may reach PRD total-size caps (≤100 MB). */
const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: "104mb",
    },
  },
};

export default nextConfig;
