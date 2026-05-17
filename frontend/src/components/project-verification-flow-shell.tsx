import type { ReactNode } from "react";

const maxWidthClass = {
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
} as const;

/**
 * Shared reading column for EPIC-12 routes: 360-first, centered and capped on md+ per design sync.
 */
export function ProjectVerificationFlowShell({
  children,
  maxWidth = "xl",
}: Readonly<{
  children: ReactNode;
  maxWidth?: keyof typeof maxWidthClass;
}>) {
  return (
    <div className="flex min-h-dvh flex-1 flex-col overflow-x-hidden bg-bg px-4 py-6 sm:px-6 lg:px-10">
      <div
        className={`mx-auto flex w-full flex-1 flex-col gap-6 ${maxWidthClass[maxWidth]}`}
      >
        {children}
      </div>
    </div>
  );
}
