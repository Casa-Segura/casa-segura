import { cookies } from "next/headers";
import type { ManualVerificationPostOk } from "@/server/project-verification-backend";
import {
  PROJECT_VERIFICATION_VERDICT_FLASH_COOKIE,
  PROJECT_VERIFICATION_VERDICT_FLASH_MAX_AGE_S,
  parseProjectVerificationVerdictFlashCookie,
  serializeProjectVerificationVerdictFlash,
  type ProjectVerificationVerdictFlashV1,
} from "@/lib/project-verification-verdict-flash";

function flashCookieOptions() {
  return {
    httpOnly: true as const,
    sameSite: "lax" as const,
    path: "/" as const,
    maxAge: PROJECT_VERIFICATION_VERDICT_FLASH_MAX_AGE_S,
    secure: process.env.NODE_ENV === "production",
  };
}

export async function setProjectVerificationVerdictFlashFromManualOk(
  ok: ManualVerificationPostOk,
): Promise<void> {
  const jar = await cookies();
  const payload: Omit<ProjectVerificationVerdictFlashV1, "v"> = {
    verdict: ok.verdict,
    headlineKey: ok.headlineKey,
    rationaleKeys: ok.rationaleKeys,
    dataFreshnessNoteKey: ok.dataFreshnessNoteKey ?? null,
    referenceId: ok.referenceId,
    heuristicScore: ok.heuristicScore,
    reputationOutcome: ok.reputationOutcome,
    reputationFetchedAt: ok.reputationFetchedAt ?? null,
    permitFindingKey: ok.permitFindingKey,
  };

  jar.set(
    PROJECT_VERIFICATION_VERDICT_FLASH_COOKIE,
    serializeProjectVerificationVerdictFlash(payload),
    flashCookieOptions(),
  );
}

export async function consumeProjectVerificationVerdictFlashCookie(): Promise<ProjectVerificationVerdictFlashV1 | null> {
  const jar = await cookies();
  const token = jar.get(PROJECT_VERIFICATION_VERDICT_FLASH_COOKIE)?.value;
  jar.delete(PROJECT_VERIFICATION_VERDICT_FLASH_COOKIE);
  return parseProjectVerificationVerdictFlashCookie(token);
}
