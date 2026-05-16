"use client";

import { forwardRef, useId, useImperativeHandle } from "react";
import {
  DISCLAIMER_EXTENDED_FOOTER,
  DISCLAIMER_GATE_LABEL,
  DISCLAIMER_SHORT,
} from "@/legal/disclaimer";

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export type DisclaimerCalloutHandle = {
  /** When `variant` is `gate`, mirrors controlled `accepted`; otherwise `true`. */
  readonly accepted: boolean;
};

type FooterOrInline = {
  variant: "footer" | "inline";
};

type Gate = {
  variant: "gate";
  accepted: boolean;
  onAcceptedChange: (accepted: boolean) => void;
};

export type DisclaimerCalloutProps = FooterOrInline | Gate;

export const DisclaimerCallout = forwardRef<
  DisclaimerCalloutHandle | null,
  DisclaimerCalloutProps
>(function DisclaimerCallout(props, ref) {
  const baseId = useId();
  const checkboxId = `${baseId}-disclaimer-accept`;

  const accepted =
    props.variant === "gate" ? props.accepted : true;

  useImperativeHandle(ref, () => ({ accepted }), [accepted]);

  switch (props.variant) {
    case "footer":
      return (
        <p className="text-center text-sm leading-snug text-text-secondary">
          <span className="font-medium text-text-primary">{DISCLAIMER_SHORT}</span>
          {". "}
          {DISCLAIMER_EXTENDED_FOOTER}
        </p>
      );
    case "inline":
      return (
        <div className="rounded-[var(--radius-input)] border border-border bg-surface p-4 text-sm leading-relaxed text-text-secondary">
          <p className="font-medium text-text-primary">{DISCLAIMER_SHORT}</p>
          <p className="mt-2">{DISCLAIMER_EXTENDED_FOOTER}</p>
        </div>
      );
    case "gate": {
      const { accepted: gateAccepted, onAcceptedChange } = props;
      return (
        <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-sm">
          <p className="text-sm font-medium leading-snug text-text-primary">
            {DISCLAIMER_SHORT}
          </p>
          <label
            htmlFor={checkboxId}
            className={`mt-4 flex cursor-pointer gap-3 rounded-[var(--radius-input)] ${focusRing}`}
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center self-start pt-0.5">
              <input
                id={checkboxId}
                type="checkbox"
                checked={gateAccepted}
                onChange={(e) => {
                  onAcceptedChange(e.target.checked);
                }}
                className={`size-5 shrink-0 rounded border-border accent-accent ${focusRing}`}
              />
            </span>
            <span className="min-h-11 flex flex-1 items-center text-base leading-snug text-text-primary">
              {DISCLAIMER_GATE_LABEL}
            </span>
          </label>
        </div>
      );
    }
  }
});
