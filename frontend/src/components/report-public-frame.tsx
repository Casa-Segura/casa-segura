"use client";

/**
 * Embeds backend-served HTML report in a sandboxed iframe (CS-294).
 * No eval; scripts inside the document are blocked by an empty sandbox attribute unless BE CSP requires a wider allowlist later.
 */
export function ReportPublicFrame({
  src,
  title,
}: {
  src: string;
  title: string;
}) {
  return (
    <iframe
      src={src}
      title={title}
      sandbox=""
      referrerPolicy="no-referrer"
      className="min-h-[75vh] w-full min-w-0 rounded-[var(--radius-card)] border border-border bg-surface print:min-h-[50vh]"
    />
  );
}
