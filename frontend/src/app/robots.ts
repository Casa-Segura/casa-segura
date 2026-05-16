import type { MetadataRoute } from "next";

/**
 * CS-298 — Preview/disallow crawl when WIP URLs are publicly reachable.
 * Override with DISALLOW_ROBOTS=true (e.g. staging on custom domain without VERCEL_ENV=preview).
 */
export default function robots(): MetadataRoute.Robots {
  const disallow =
    process.env.VERCEL_ENV === "preview" ||
    process.env.DISALLOW_ROBOTS === "1" ||
    process.env.DISALLOW_ROBOTS === "true";

  if (disallow) {
    return {
      rules: { userAgent: "*", disallow: "/" },
    };
  }
  return {
    rules: { userAgent: "*", allow: "/" },
  };
}
