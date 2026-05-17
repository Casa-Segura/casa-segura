"use client";

import Image from "next/image";
import Link from "next/link";
import { useActionState, useEffect, useRef, useState } from "react";
import {
  submitProjectVerificationBillboardUpload,
  type BillboardUploadFormState,
} from "@/app/verificacion-proyecto/foto/actions";

const initialState: BillboardUploadFormState | null = null;

function formErrorFromState(
  state: BillboardUploadFormState | null,
): string | null {
  if (!state || state.ok) return null;
  return state.formError;
}

export function ProjectVerificationBillboardUploadForm() {
  const [state, formAction, pending] = useActionState(
    submitProjectVerificationBillboardUpload,
    initialState,
  );
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const formErrorRef = useRef<HTMLParagraphElement>(null);

  const formError = formErrorFromState(state);

  useEffect(() => {
    if (state?.ok && statusRef.current) {
      statusRef.current.focus();
    }
    if (formError && formErrorRef.current) {
      formErrorRef.current.focus();
    }
  }, [state, formError]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return (
    <form action={formAction} className="flex flex-col gap-5" noValidate>
      <div className="rounded-[var(--radius-card)] border border-border bg-accent-light/50 p-4 text-sm leading-relaxed text-text-primary">
        <p className="font-medium">La foto se usa solo para este intento.</p>
        <p className="mt-2 text-text-secondary">
          Buscamos señales visibles del proyecto. Si la lectura queda
          incompleta, vas a poder corregir los datos a mano.
        </p>
      </div>

      {formError ? (
        <p
          ref={formErrorRef}
          id="billboard-upload-error"
          tabIndex={-1}
          role="alert"
          className="rounded-[var(--radius-input)] border border-verdict-red/40 bg-verdict-red-bg p-4 text-sm leading-relaxed text-verdict-red outline-none"
        >
          {formError}
        </p>
      ) : null}

      <div className="flex flex-col gap-2">
        <label
          htmlFor="billboard"
          className="text-sm font-medium text-text-primary"
        >
          Foto de la valla
        </label>
        <input
          id="billboard"
          name="billboard"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif"
          capture="environment"
          aria-describedby={
            formError
              ? "billboard-upload-error billboard-help"
              : "billboard-help"
          }
          aria-invalid={Boolean(formError)}
          onChange={(event) => {
            const file = event.currentTarget.files?.[0] ?? null;
            setFileName(file?.name ?? null);
            setPreviewUrl((current) => {
              if (current) URL.revokeObjectURL(current);
              return file ? URL.createObjectURL(file) : null;
            });
          }}
          className="min-h-[44px] rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary file:mr-3 file:min-h-[36px] file:rounded-[var(--radius-input)] file:border-0 file:bg-accent file:px-3 file:text-sm file:font-semibold file:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        />
        <p
          id="billboard-help"
          className="text-sm leading-relaxed text-text-secondary"
        >
          JPEG, PNG, WEBP o HEIC. Máximo 15 MB. En móvil podés abrir la cámara
          desde este campo.
        </p>
      </div>

      {previewUrl ? (
        <figure className="overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface shadow-sm">
          <Image
            src={previewUrl}
            alt="Vista previa de la foto seleccionada"
            width={720}
            height={480}
            unoptimized
            className="aspect-[3/2] w-full object-cover"
          />
          <figcaption className="border-t border-border px-4 py-3 text-sm text-text-secondary">
            {fileName ? `Archivo listo: ${fileName}` : "Archivo listo."}
          </figcaption>
        </figure>
      ) : (
        <div className="rounded-[var(--radius-card)] border border-dashed border-border bg-surface p-5 text-sm leading-relaxed text-text-secondary">
          Todavía no elegiste una foto. Buscá una toma donde se lea el nombre
          del proyecto, desarrollador, permiso y dirección si aparecen.
        </div>
      )}

      <button
        type="submit"
        disabled={pending}
        className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 active:translate-y-px active:opacity-100 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {pending ? "Enviando foto…" : "Enviar foto de valla"}
      </button>

      {state?.ok ? (
        <div
          ref={statusRef}
          tabIndex={-1}
          role="status"
          aria-live="polite"
          className="rounded-[var(--radius-input)] border border-border bg-accent-light/50 p-4 text-sm leading-relaxed text-text-primary outline-none"
        >
          <p className="font-medium">{state.message}</p>
          {state.detail ? (
            <p className="mt-2 text-text-secondary">{state.detail}</p>
          ) : null}
          <Link
            href="/verificacion-proyecto/manual"
            className="mt-3 inline-flex min-h-[44px] items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-2 font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Completar o corregir a mano
          </Link>
        </div>
      ) : null}
    </form>
  );
}
