/**
 * FE deployment gate for optional project / billboard verification (CS-356).
 * Default-off: unset or empty → disabled (safe for prod rollouts).
 */

export function isProjectVerificationEnabled(): boolean {
  const raw = process.env.PROJECT_VERIFICATION_ENABLED?.trim().toLowerCase();
  if (!raw) return false;
  return raw === "true" || raw === "1" || raw === "yes";
}
