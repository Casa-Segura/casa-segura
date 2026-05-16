import type { NextConfig } from "next";

/**
 * CS-298 — Fail Vercel builds when `CASASEGURA_API_BASE_URL` is missing so Preview/Production cannot
 * ship pointing at nowhere. CI and local builds omit VERCEL unless explicitly set.
 */
if (
  process.env.NODE_ENV === "production" &&
  process.env.VERCEL === "1" &&
  !process.env.CASASEGURA_API_BASE_URL?.trim()
) {
  throw new Error(
    "[CS-298] CASASEGURA_API_BASE_URL is required for Vercel builds. Configure it under Project Settings → Environment Variables (Preview + Production). See frontend/README.md (Vercel deployment).",
  );
}

/** Multipart payloads may reach PRD total-size caps (≤100 MB). */
const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: "104mb",
    },
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
