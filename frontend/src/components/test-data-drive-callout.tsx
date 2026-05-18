"use client";

import { ArrowSquareOut } from "@phosphor-icons/react";
import { cx, focusRing } from "@/components/casa-ui";
import { PUBLIC_TEST_DATA_DRIVE_URL } from "@/lib/site";

const driveLinkClassName = cx(
  "inline-flex min-h-[48px] items-center justify-center gap-2 rounded-[var(--radius-input)] border border-border bg-surface px-5 py-3 text-center text-base font-semibold text-accent shadow-sm transition-[background-color,transform] duration-[var(--motion-fast)] hover:bg-accent-light active:translate-y-px",
  focusRing,
);

type TestDataDriveCalloutProps = {
  variant?: "landing" | "compact";
  className?: string;
  headingId?: string;
};

export function TestDataDriveCallout({
  variant = "landing",
  className,
  headingId = "test-data-heading",
}: TestDataDriveCalloutProps) {
  const driveLink = (
    <a
      href={PUBLIC_TEST_DATA_DRIVE_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Abrir la carpeta de datos de prueba en Google Drive en una pestaña nueva"
      className={cx(
        driveLinkClassName,
        variant === "landing" && "w-full lg:w-auto lg:self-center",
        variant === "compact" && "w-full text-sm",
      )}
    >
      Abrir carpeta en Google Drive
      <ArrowSquareOut className="h-5 w-5 shrink-0" weight="bold" aria-hidden />
    </a>
  );

  const bodyCopy = (
    <p
      className={cx(
        "leading-relaxed text-text-secondary",
        variant === "landing"
          ? "max-w-[62ch] text-sm sm:text-base"
          : "text-sm",
      )}
    >
      Los PDF y la imagen de muestra están pensados para{" "}
      <span className="font-medium text-text-primary">El Salvador</span>; el
      mismo flujo aplica a proyectos en{" "}
      <span className="font-medium text-text-primary">LATAM</span> cuando sumemos
      más ejemplos regionales.
    </p>
  );

  if (variant === "compact") {
    return (
      <aside
        className={cx(
          "rounded-[var(--radius-card)] border border-dashed border-border bg-surface-muted/80 p-4",
          className,
        )}
        aria-labelledby={headingId}
      >
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          Probá sin inventar archivos
        </p>
        <h2
          id={headingId}
          className="mt-2 text-balance text-lg font-semibold tracking-tight text-text-primary"
        >
          Datos de prueba
        </h2>
        <div className="mt-2">{bodyCopy}</div>
        <div className="mt-4">{driveLink}</div>
      </aside>
    );
  }

  return (
    <section
      className={cx(
        "grid gap-6 rounded-[var(--radius-panel)] border border-border bg-surface p-6 shadow-[var(--shadow-soft)] lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:gap-10 lg:p-8",
        className,
      )}
      aria-labelledby={headingId}
    >
      <div className="flex flex-col gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          Probá sin inventar archivos
        </p>
        <h2
          id={headingId}
          className="text-balance text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl"
        >
          Datos de prueba listos para usar
        </h2>
        {bodyCopy}
      </div>
      {driveLink}
    </section>
  );
}
