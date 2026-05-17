"use client";

import { Trash } from "@phosphor-icons/react";
import Image from "next/image";
import Link from "next/link";
import { useActionState, useCallback, useEffect, useRef, useState } from "react";
import {
  submitProjectVerificationBillboardUpload,
  type BillboardUploadFormState,
} from "@/app/verificacion-proyecto/foto/actions";
import { cx, focusRing } from "@/components/casa-ui";
import { buildManualVerificationHandoffPath } from "@/lib/project-verification-manual-handoff";

const manualAfterBillboardHref = buildManualVerificationHandoffPath({
  source: "billboard_stub_continue",
});

const initialState: BillboardUploadFormState | null = null;

export type BillboardDesktopCompanionPhase = "idle" | "loading" | "complete";

export type BillboardPhotoPreviewPayload = {
  objectUrl: string | null;
  fileName: string | null;
};

function formErrorFromState(
  state: BillboardUploadFormState | null,
): string | null {
  if (!state || state.ok) return null;
  return state.formError;
}

export function ProjectVerificationBillboardUploadForm({
  onCompanionPhaseChange,
  onPreviewChange,
}: {
  /** Sincroniza la mesa de escritorio `/subir` (valla) con el estado del envío. */
  onCompanionPhaseChange?: (phase: BillboardDesktopCompanionPhase) => void;
  /** Vista previa en la mesa de escritorio (blob URL + nombre). */
  onPreviewChange?: (preview: BillboardPhotoPreviewPayload) => void;
} = {}) {
  const [state, formAction, pending] = useActionState(
    submitProjectVerificationBillboardUpload,
    initialState,
  );
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const billboardInputRef = useRef<HTMLInputElement>(null);
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

  useEffect(() => {
    if (!onCompanionPhaseChange) return;
    const phase: BillboardDesktopCompanionPhase = pending
      ? "loading"
      : state?.ok
        ? "complete"
        : "idle";
    onCompanionPhaseChange(phase);
  }, [pending, state?.ok, onCompanionPhaseChange]);

  useEffect(() => {
    onPreviewChange?.({ objectUrl: previewUrl, fileName });
  }, [previewUrl, fileName, onPreviewChange]);

  const clearSelectedPhoto = useCallback(() => {
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setFileName(null);
    const input = billboardInputRef.current;
    if (input) input.value = "";
  }, []);

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
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch sm:gap-3">
          <input
            ref={billboardInputRef}
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
            className="min-h-[44px] min-w-0 flex-1 rounded-[var(--radius-input)] border border-border bg-surface px-3 py-2 text-base text-text-primary file:mr-3 file:min-h-[36px] file:rounded-[var(--radius-input)] file:border-0 file:bg-accent file:px-3 file:text-sm file:font-semibold file:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          />
          {previewUrl ? (
            <button
              type="button"
              onClick={clearSelectedPhoto}
              disabled={pending}
              aria-label="Quitar foto seleccionada"
              className={cx(
                "inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-[var(--radius-input)] border border-border bg-surface px-4 text-sm font-semibold text-text-primary shadow-sm transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50",
                focusRing,
              )}
            >
              <Trash size={18} aria-hidden />
              Quitar foto
            </button>
          ) : null}
        </div>
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
            alt={
              fileName?.trim()
                ? `Vista previa del archivo seleccionado: ${fileName}`
                : "Vista previa del archivo seleccionado"
            }
            width={720}
            height={480}
            unoptimized
            sizes="(max-width: 768px) 100vw, 560px"
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
            href={manualAfterBillboardHref}
            className="mt-3 inline-flex min-h-[44px] items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-2 font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Completar o corregir a mano
          </Link>
        </div>
      ) : null}
    </form>
  );
}
