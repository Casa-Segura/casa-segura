"use client";

import { useActionState, useEffect, useRef } from "react";
import {
  submitProjectVerificationManual,
  type ManualFormState,
} from "@/app/verificacion-proyecto/manual/actions";

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
        <input
          id="developer"
          name="developer"
          type="text"
          autoComplete="organization"
          defaultValue={initialValues?.developer ?? ""}
          aria-invalid={Boolean(fieldErrors?.developer)}
          aria-describedby={
            fieldErrors?.developer
              ? "developer-err"
              : formError
                ? `manual-form-error ${baseDescription}`
                : baseDescription
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
        <input
          id="permit"
          name="permit"
          type="text"
          autoComplete="off"
          defaultValue={initialValues?.permit ?? ""}
          aria-invalid={Boolean(fieldErrors?.permit)}
          aria-describedby={
            fieldErrors?.permit
              ? "permit-err"
              : formError
                ? `manual-form-error ${baseDescription}`
                : baseDescription
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
        <input
          id="address"
          name="address"
          type="text"
          autoComplete="street-address"
          defaultValue={initialValues?.address ?? ""}
          aria-invalid={Boolean(fieldErrors?.address)}
          aria-describedby={
            fieldErrors?.address
              ? "address-err"
              : formError
                ? `manual-form-error ${baseDescription}`
                : baseDescription
          }
          className="min-h-[44px] rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent"
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
        className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {pending ? "Enviando…" : "Enviar verificación"}
      </button>

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
