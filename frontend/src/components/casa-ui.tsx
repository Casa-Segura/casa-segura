"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";
import type { LinkProps } from "next/link";
import {
  ArrowRight,
  CheckCircle,
  FileText,
  Info,
  Scales,
  ShieldCheck,
  Warning,
  XCircle,
} from "@phosphor-icons/react";

export const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type Tone = "neutral" | "accent" | "green" | "yellow" | "red";

const toneClasses: Record<Tone, string> = {
  neutral: "border-border bg-surface text-text-primary",
  accent: "border-accent/20 bg-accent-light text-accent",
  green: "border-verdict-green/30 bg-verdict-green-bg text-verdict-green",
  yellow: "border-verdict-yellow/30 bg-verdict-yellow-bg text-verdict-yellow",
  red: "border-verdict-red/30 bg-verdict-red-bg text-verdict-red",
};

export function BrandMark({
  label = "Casa Segura",
  inverse = false,
}: {
  label?: string;
  inverse?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2.5" translate="no">
      <span className="inline-flex size-8 items-center justify-center rounded-[8px] bg-accent text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.2)]">
        <ShieldCheck size={18} weight="bold" aria-hidden />
      </span>
      <span
        className={cx(
          "text-sm font-semibold tracking-tight",
          inverse ? "text-white/90" : "text-text-primary",
        )}
      >
        {label}
      </span>
    </span>
  );
}

type CasaButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export function CasaButton({
  variant = "primary",
  className,
  type = "button",
  ...props
}: CasaButtonProps) {
  const variantClass =
    variant === "primary"
      ? "border-accent bg-accent text-white hover:bg-accent/95 active:translate-y-px"
      : variant === "secondary"
        ? "border-accent bg-surface text-accent hover:bg-accent-light active:translate-y-px"
        : "border-transparent bg-transparent text-accent hover:bg-accent-light active:translate-y-px";

  return (
    <button
      {...props}
      type={type}
      className={cx(
        "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-[var(--radius-input)] border px-4 py-2 text-base font-semibold transition-[background-color,border-color,color,opacity,transform] duration-[var(--motion-fast)] touch-manipulation disabled:cursor-not-allowed disabled:opacity-50",
        focusRing,
        variantClass,
        className,
      )}
    />
  );
}

type CasaLinkButtonProps = LinkProps & {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "ghost";
};

export function CasaLinkButton({
  variant = "primary",
  className,
  children,
  ...props
}: CasaLinkButtonProps) {
  const variantClass =
    variant === "primary"
      ? "border-accent bg-accent text-white hover:bg-accent/95 active:translate-y-px"
      : variant === "secondary"
        ? "border-accent bg-surface text-accent hover:bg-accent-light active:translate-y-px"
        : "border-transparent bg-transparent text-accent hover:bg-accent-light active:translate-y-px";

  return (
    <Link
      {...props}
      className={cx(
        "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-[var(--radius-input)] border px-4 py-2 text-base font-semibold transition-[background-color,border-color,color,opacity,transform] duration-[var(--motion-fast)] touch-manipulation",
        focusRing,
        variantClass,
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function StepPill({
  children,
  tone = "accent",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex w-fit items-center gap-2 rounded-[var(--radius-pill)] border px-3 py-1.5 text-xs font-semibold",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusPill({
  children,
  tone = "accent",
  pulse = false,
}: {
  children: ReactNode;
  tone?: Tone;
  pulse?: boolean;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-2 rounded-[var(--radius-pill)] border px-3 py-1.5 text-xs font-medium",
        toneClasses[tone],
      )}
    >
      <span
        className={cx(
          "size-1.5 rounded-full bg-current",
          pulse && "motion-safe:animate-[casa-pulse-soft_1.8s_ease-in-out_infinite]",
        )}
        aria-hidden
      />
      {children}
    </span>
  );
}

export function DisclaimerPanel({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <aside
      className={cx(
        "flex gap-3 rounded-[var(--radius-card)] border p-4 text-sm leading-relaxed shadow-[var(--shadow-soft)]",
        toneClasses[tone],
      )}
    >
      <Info size={20} weight="regular" className="mt-0.5 shrink-0" aria-hidden />
      <div className="min-w-0">{children}</div>
    </aside>
  );
}

export function SkeletonBlock({
  className,
  label = "Cargando",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <span
      aria-label={label}
      className={cx(
        "relative block overflow-hidden rounded-[8px] bg-border/70 before:absolute before:inset-y-0 before:left-[-100%] before:w-full before:bg-gradient-to-r before:from-transparent before:via-white/60 before:to-transparent motion-safe:before:animate-[casa-shimmer_1.35s_ease-in-out_infinite] motion-reduce:before:hidden",
        className,
      )}
    />
  );
}

export type ProgressStep = {
  id: string;
  label: string;
  detail: string;
  state: "done" | "active" | "pending" | "error";
};

export function ProgressTimeline({
  steps,
  progress,
}: {
  steps: readonly ProgressStep[];
  progress: number;
}) {
  return (
    <div className="flex flex-col gap-4" aria-live="polite">
      <ol className="overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={cx(
              "flex items-start gap-3 border-b border-border px-4 py-3 last:border-b-0",
              step.state === "active" && "bg-accent-light/70",
              step.state === "error" && "bg-verdict-red-bg",
            )}
          >
            <StepIcon state={step.state} index={index + 1} />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-text-primary">
                {step.label}
              </span>
              <span className="mt-0.5 block text-xs leading-relaxed text-text-secondary">
                {step.detail}
              </span>
            </span>
          </li>
        ))}
      </ol>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <span>Progreso</span>
          <span className="font-mono text-accent tabular-nums">
            {Math.max(0, Math.min(100, progress))}%
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-[var(--motion-slow)]"
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function StepIcon({
  state,
  index,
}: {
  state: ProgressStep["state"];
  index: number;
}) {
  if (state === "done") {
    return (
      <CheckCircle
        size={24}
        weight="fill"
        className="shrink-0 text-verdict-green"
        aria-hidden
      />
    );
  }
  if (state === "error") {
    return (
      <XCircle
        size={24}
        weight="fill"
        className="shrink-0 text-verdict-red"
        aria-hidden
      />
    );
  }
  return (
    <span
      className={cx(
        "inline-flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
        state === "active"
          ? "bg-accent text-white motion-safe:animate-[casa-pulse-soft_1.8s_ease-in-out_infinite]"
          : "bg-border text-text-secondary",
      )}
      aria-hidden
    >
      {index}
    </span>
  );
}

export function FindingCard({
  tone,
  title,
  body,
  citation,
}: {
  tone: Exclude<Tone, "neutral" | "accent">;
  title: string;
  body: string;
  citation?: string;
}) {
  const Icon = tone === "green" ? CheckCircle : tone === "yellow" ? Warning : XCircle;
  return (
    <article className="rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)]">
      <div className="flex gap-3">
        <span
          className={cx(
            "inline-flex size-8 shrink-0 items-center justify-center rounded-full",
            tone === "green" && "bg-verdict-green-bg text-verdict-green",
            tone === "yellow" && "bg-verdict-yellow-bg text-verdict-yellow",
            tone === "red" && "bg-verdict-red-bg text-verdict-red",
          )}
        >
          <Icon size={18} weight="fill" aria-hidden />
        </span>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-text-secondary">
            {body}
          </p>
          {citation ? (
            <p className="mt-3 inline-flex items-center gap-1.5 rounded-[var(--radius-pill)] bg-accent-light px-2.5 py-1 text-xs font-medium text-accent">
              <Scales size={13} aria-hidden />
              {citation}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function LegalSummary({
  children,
  title = "Base legal de este resultado",
}: {
  children: ReactNode;
  title?: string;
}) {
  return (
    <section className="rounded-[var(--radius-card)] border border-accent-light bg-[#F0F7F6] p-4">
      <div className="flex items-center gap-2 text-accent">
        <Scales size={20} aria-hidden />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="mt-3 text-sm leading-relaxed text-text-primary">
        {children}
      </div>
    </section>
  );
}

export function DocumentPreview({
  active = false,
  className,
}: {
  active?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "rounded-[var(--radius-panel)] border border-border bg-document-bg p-4 shadow-[var(--shadow-panel)]",
        className,
      )}
      aria-label="Vista previa del contrato"
    >
      <div className="mb-3 flex items-center justify-between rounded-[var(--radius-input)] border border-border bg-surface-subtle px-3 py-2 text-xs text-text-secondary">
        <span className="inline-flex items-center gap-2">
          <FileText size={14} aria-hidden />
          Contrato_Venta_Rivas.pdf
        </span>
        <span>Página 1 de 4</span>
      </div>
      <div className="min-h-[360px] rounded-[10px] bg-surface p-6 shadow-sm">
        <div className="mb-7 h-3 w-40 rounded-full bg-border" />
        <DocumentLine width="w-full" />
        <DocumentLine width="w-11/12" />
        <DocumentLine width="w-10/12" />
        <DocumentHighlight tone="green" active={active} />
        <DocumentLine width="w-full" />
        <DocumentLine width="w-9/12" />
        <DocumentHighlight tone="red" active={active} />
        <DocumentLine width="w-11/12" />
        <DocumentLine width="w-8/12" />
        <DocumentHighlight tone="yellow" active={active} />
        <DocumentLine width="w-full" />
        <DocumentLine width="w-10/12" />
      </div>
    </div>
  );
}

function DocumentLine({ width }: { width: string }) {
  return <div className={cx("mb-2 h-2 rounded-full bg-border", width)} />;
}

function DocumentHighlight({
  tone,
  active,
}: {
  tone: "green" | "yellow" | "red";
  active: boolean;
}) {
  return (
    <div
      className={cx(
        "my-3 h-3 rounded-full transition-[opacity,transform] duration-[var(--motion-slow)]",
        active && "motion-safe:animate-[casa-pulse-soft_2.2s_ease-in-out_infinite]",
        tone === "green" && "bg-verdict-green/45",
        tone === "yellow" && "bg-verdict-yellow/45",
        tone === "red" && "bg-verdict-red/45",
      )}
    />
  );
}

export function ArrowCta() {
  return <ArrowRight size={18} weight="bold" aria-hidden />;
}
