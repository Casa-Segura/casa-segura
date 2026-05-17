/**
 * FE deployment gate for optional project / billboard verification (CS-356).
 * Default-off: unset or empty → disabled (safe for prod rollouts).
 */

export function isProjectVerificationEnabled(): boolean {
  const raw = process.env.PROJECT_VERIFICATION_ENABLED?.trim().toLowerCase();
  if (!raw) return false;
  return raw === "true" || raw === "1" || raw === "yes";
}

/** Enables demo band switchers on resultado (staging/prod stays off unless explicitly enabled). */
export function isProjectVerificationDemoLinksEnabled(): boolean {
  if (process.env.NODE_ENV === "development") return true;
  const raw = process.env.PROJECT_VERIFICATION_DEMO_LINKS?.trim().toLowerCase();
  return raw === "true" || raw === "1" || raw === "yes";
}
