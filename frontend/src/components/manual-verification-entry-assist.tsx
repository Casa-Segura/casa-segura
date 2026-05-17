"use client";

import { useEffect, useRef } from "react";
import { recordManualFormHandoffTelemetry } from "@/app/verificacion-proyecto/manual/telemetry-actions";
import type { ManualHandoffSource } from "@/lib/project-verification-manual-handoff";

/** One-shot server telemetry + landmark focus after navigation to `/manual`. */
export function ManualVerificationEntryAssist({
  source,
}: Readonly<{
  source: ManualHandoffSource | undefined;
}>) {
  const reported = useRef(false);

  useEffect(() => {
    if (reported.current) return;
    reported.current = true;
    void recordManualFormHandoffTelemetry(source);

    const frame = window.requestAnimationFrame(() => {
      const main = document.getElementById("main-content");
      if (main && typeof main.focus === "function") {
        main.focus();
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [source]);

  return null;
}
