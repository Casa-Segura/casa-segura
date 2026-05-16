import { notFound } from "next/navigation";
import { isProjectVerificationEnabled } from "@/lib/project-verification-env";

/** Env gate must run per deployment/request — avoid baking `PROJECT_VERIFICATION_ENABLED` at build time. */
export const dynamic = "force-dynamic";

/**
 * When the gate is off, all routes under this segment return 404 via `not-found.tsx`
 * (CS-356 — optional flow must not look half-enabled).
 */
export default function ProjectVerificationLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  if (!isProjectVerificationEnabled()) {
    notFound();
  }
  return children;
}
