"use client";

import Link from "next/link";
import { useActionState, useEffect, useRef } from "react";
import {
  submitProjectVerificationManual,
  type ManualFormState,
} from "@/app/verificacion-proyecto/manual/actions";
import { cx, focusRing } from "@/components/casa-ui";

const initialState: ManualFormState | null = null;

type ManualFormInitialValues = {
  developer?: string;
  project?: string;
  permit?: string;
  address?: string;
};

function fieldErrorsFromState(
  state: ManualFormState | null,
): Record<string, string> | null {
  if (!state || state.ok) return null;
  if ("fieldErrors" in state) return state.fieldErrors;
  return null;
}

function formErrorFromState(state: ManualFormState | null): string | null {
  if (!state || state.ok) return null;
  if ("formError" in state) return state.formError;
  return null;
}

export function ProjectVerificationManualForm({
  initialValues,
  prefillNote,
}: {
  initialValues?: ManualFormInitialValues;
  prefillNote?: string;
}) {
  const [state, formAction, pending] = useActionState(
    submitProjectVerificationManual,
    initialState,
  );
  const statusRef = useRef<HTMLParagraphElement>(null);
  const formErrorRef = useRef<HTMLParagraphElement>(null);

  const fieldErrors = fieldErrorsFromState(state);
  const formError = formErrorFromState(state);
  const baseDescription = prefillNote
    ? "manual-form-desc manual-prefill-note"
    : "manual-form-desc";

  useEffect(() => {
    if (state?.ok && statusRef.current) {
      statusRef.current.focus();
    }
    if (formError && formErrorRef.current) {
      formErrorRef.current.focus();
    }
  }, [state, formError]);

  return (
    <form action={formAction} className="flex flex-col gap-5" noValidate>
      <p
        id="manual-form-desc"
        className="text-sm leading-relaxed text-text-secondary"
      >
        Completá los campos con la información que tengas a mano. No subimos
        PDFs ni fotos acá todavía.
      </p>

      {prefillNote ? (
        <p
          id="manual-prefill-note"
          className="rounded-[var(--radius-input)] border border-border bg-accent-light/50 p-4 text-sm leading-relaxed text-text-primary"
        >
          {prefillNote}
        </p>
      ) : null}

      {formError ? (
        <p
          ref={formErrorRef}
          id="manual-form-error"
          tabIndex={-1}
          role="alert"
          className="rounded-[var(--radius-input)] border border-verdict-red/40 bg-verdict-red-bg p-4 text-sm leading-relaxed text-verdict-red outline-none"
        >
          {formError}
        </p>
      ) : null}

      <div className="flex flex-col gap-2">
        <label
          htmlFor="developer"
          className="text-sm font-medium text-text-primary"
        >
          Desarrollador / constructor
        </label>
        <p
          id="developer-hint"
          className="text-xs leading-snug text-text-secondary"
        >
          Usá el nombre visible en el cartel o material del proyecto.
        </p>
        <input
          id="developer"
          name="developer"
          type="text"
          autoComplete="organization"
          defaultValue={initialValues?.developer ?? ""}
          aria-invalid={Boolean(fieldErrors?.developer)}
          aria-describedby={
            fieldErrors?.developer
              ? "developer-err developer-hint"
              : formError
                ? `manual-form-error developer-hint ${baseDescription}`
                : `developer-hint ${baseDescription}`
          }
          className="min-h-[44px] rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        {fieldErrors?.developer ? (
          <p
            id="developer-err"
            role="alert"
            className="text-sm text-verdict-red"
          >
            {fieldErrors.developer}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="project"
          className="text-sm font-medium text-text-primary"
        >
          Nombre del proyecto
        </label>
        <input
          id="project"
          name="project"
          type="text"
          autoComplete="off"
          defaultValue={initialValues?.project ?? ""}
          aria-invalid={Boolean(fieldErrors?.project)}
          aria-describedby={
            fieldErrors?.project
              ? "project-err"
              : formError
                ? `manual-form-error ${baseDescription}`
                : baseDescription
          }
          className="min-h-[44px] rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        {fieldErrors?.project ? (
          <p id="project-err" role="alert" className="text-sm text-verdict-red">
            {fieldErrors.project}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="permit"
          className="text-sm font-medium text-text-primary"
        >
          Permiso / expediente
        </label>
        <p
          id="permit-hint"
          className="text-xs leading-snug text-text-secondary"
        >
          Números y guiones tal como aparecen en la valla, si los tenés.
        </p>
        <input
          id="permit"
          name="permit"
          type="text"
          autoComplete="off"
          defaultValue={initialValues?.permit ?? ""}
          aria-invalid={Boolean(fieldErrors?.permit)}
          aria-describedby={
            fieldErrors?.permit
              ? "permit-err permit-hint"
              : formError
                ? `manual-form-error permit-hint ${baseDescription}`
                : `permit-hint ${baseDescription}`
          }
          className="min-h-[44px] rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        {fieldErrors?.permit ? (
          <p id="permit-err" role="alert" className="text-sm text-verdict-red">
            {fieldErrors.permit}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="address"
          className="text-sm font-medium text-text-primary"
        >
          Dirección aproximada
        </label>
        <p
          id="address-hint"
          className="text-xs leading-snug text-text-secondary"
        >
          Municipio o punto de referencia; no necesitamos la dirección catastral
          completa.
        </p>
        <textarea
          id="address"
          name="address"
          rows={3}
          autoComplete="street-address"
          defaultValue={initialValues?.address ?? ""}
          aria-invalid={Boolean(fieldErrors?.address)}
          aria-describedby={
            fieldErrors?.address
              ? "address-err address-hint"
              : formError
                ? `manual-form-error address-hint ${baseDescription}`
                : `address-hint ${baseDescription}`
          }
          className="min-h-[88px] w-full resize-y rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base leading-relaxed text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        {fieldErrors?.address ? (
          <p id="address-err" role="alert" className="text-sm text-verdict-red">
            {fieldErrors.address}
          </p>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={pending}
        aria-busy={pending}
        className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {pending ? (
          <>
            <span
              aria-hidden
              className="mr-2 inline-block size-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none"
            />
            Verificando…
          </>
        ) : (
          "Verificar proyecto"
        )}
      </button>

      <p className="text-center">
        <Link
          href="/verificacion-proyecto/foto"
          className={cx(
            "inline-flex min-h-[44px] items-center justify-center text-sm font-medium text-accent underline-offset-4 hover:underline",
            focusRing,
            "rounded-sm px-1",
          )}
        >
          Cancelar: volver a la foto
        </Link>
      </p>

      {state?.ok ? (
        <p
          ref={statusRef}
          tabIndex={-1}
          role="status"
          className="rounded-[var(--radius-input)] border border-border bg-accent-light/50 p-4 text-sm leading-relaxed text-text-primary outline-none"
        >
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
