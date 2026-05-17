"use client";

import { CheckCircle } from "@phosphor-icons/react";

export function ManualVerificationSuccessBadge() {
  return (
    <span
      aria-hidden
      className="flex size-14 shrink-0 items-center justify-center rounded-full bg-verdict-green-bg text-verdict-green ring-2 ring-verdict-green/30"
    >
      <CheckCircle size={32} weight="duotone" />
    </span>
  );
}
