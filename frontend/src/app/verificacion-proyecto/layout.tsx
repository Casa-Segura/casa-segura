import { redirect } from "next/navigation";

/** Evaluate redirects per request — avoid baking route behaviour at build time. */
export const dynamic = "force-dynamic";

/**
 * Optional billboard verification was retired from the public UI; deep links land on home.
 * Backend gates under `PROJECT_VERIFICATION_*` still apply for API rehearsal.
 */
export default function ProjectVerificationLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  void children;
  redirect("/");
}
