import Link from "next/link";
import { ContractUploadFlow } from "@/components/contract-upload-flow";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

/** CS-291: mobile-first `/subir` — CS-292 delivery picker + CS-296 server actions wired to CASASEGURA_* env. */

export default function SubirContratoPage() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
        <main className="flex flex-1 flex-col rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
          <ContractUploadFlow />
        </main>
        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
