"use client";

import type { DragEvent } from "react";
import { useCallback, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { submitContractUploadFlow } from "@/actions/contract-flow";
import { ContractAnalysisLoadingPanel } from "@/components/contract-analysis-loading-panel";
import { DisclaimerCallout } from "@/components/disclaimer-callout";
import { DeliveryChannelFields } from "@/components/delivery-channel-fields";
import {
  CONTRACT_ACCEPTABLE_EXTENSIONS,
  CONTRACT_ACCEPTABLE_MIME_TYPES,
  CONTRACT_MAX_FILE_BYTES,
  CONTRACT_MAX_FILE_COUNT,
  CONTRACT_MAX_TOTAL_BYTES,
} from "@/domain/contract-upload-constants";
import {
  defaultDeliveryDraft,
  type DeliveryDraft,
  validateDeliveryForSubmit,
} from "@/domain/delivery-channel";

const focusBtn =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

type Phase = "empty" | "selected";

function mimeFromFilename(name: string): string | undefined {
  const ext = name.split(".").pop()?.toLowerCase();
  if (!ext) return undefined;
  if (ext === "jpg" || ext === "jpeg") return "image/jpeg";
  const map = {
    pdf: "application/pdf",
    png: "image/png",
    heic: "image/heic",
    webp: "image/webp",
  } as const;
  return map[ext as keyof typeof map];
}

function classifyClientFileReject(file: File): string | null {
  const name = file.name.toLowerCase();
  const dot = name.lastIndexOf(".");
  const ext = dot >= 0 ? name.slice(dot + 1) : "";
  if (!CONTRACT_ACCEPTABLE_EXTENSIONS.has(ext)) {
    return "Sólo aceptamos PDF, JPEG/PNG/HEIC y WEBP. Convertí o exportá antes de intentar.";
  }
  let mimeOk = CONTRACT_ACCEPTABLE_MIME_TYPES.some((t) => file.type === t);
  if (!mimeOk && file.type === "")
    mimeOk = Boolean(mimeFromFilename(file.name));
  if (!mimeOk)
    return "Uno de los archivos no coincide con ningún formato que podamos revisar desde el móvil.";
  if (file.size > CONTRACT_MAX_FILE_BYTES) {
    return "Hay un archivo de más de 15 MB por archivo — comprime PDF o fotografía mejorada antes de mandar.";
  }
  return null;
}

export function ContractUploadFlow() {
  const router = useRouter();
  const baseId = useId();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const disclaimerScrollRef = useRef<HTMLDivElement | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [delivery, setDelivery] = useState<DeliveryDraft>(() =>
    defaultDeliveryDraft(),
  );
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<"email" | "phone", string>>
  >({});
  const [deliveryBanner, setDeliveryBanner] = useState<string>("");

  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [phase, setPhase] = useState<Phase>("empty");
  const [busy, setBusy] = useState(false);
  const [loadingSession, setLoadingSession] = useState(0);

  const [globalError, setGlobalError] = useState("");
  const [disclaimerReminder, setDisclaimerReminder] = useState(false);
  const [result, setResult] = useState<
    | { kind: "success"; submissionId: string; hint: string }
    | { kind: "reject"; reasons: string[] }
    | null
  >(null);

  const acceptAttr = useMemo(
    () => CONTRACT_ACCEPTABLE_MIME_TYPES.join(","),
    [],
  );

  const ingestClientFiles = useCallback(
    (incoming: readonly File[]) => {
      const next: File[] = [...files];
      const errors: string[] = [];
      for (const raw of incoming) {
        const reason = classifyClientFileReject(raw);
        if (reason) {
          errors.push(reason);
          continue;
        }
        next.push(raw);
      }
      if (next.length > CONTRACT_MAX_FILE_COUNT) {
        setGlobalError(
          "Sólo podés subir hasta 50 archivos a la vez. Quitá algunos para continuar.",
        );
        return;
      }
      const accum = next.reduce((a, b) => a + b.size, 0);
      if (accum > CONTRACT_MAX_TOTAL_BYTES) {
        setGlobalError(
          `En conjunto superan los ${Math.round(CONTRACT_MAX_TOTAL_BYTES / (1024 * 1024))} MB máximos. Eliminá algunos archivos.`,
        );
        return;
      }
      if (errors.length) setGlobalError(errors[0] ?? "");

      next.sort((a, b) => a.name.localeCompare(b.name));
      setFiles(next);
      setPhase(next.length ? "selected" : "empty");
      if (!errors.length) setGlobalError("");
    },
    [files],
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const sel = [...(e.target.files ?? [])];
    e.target.value = "";
    if (!sel.length) return;
    ingestClientFiles(sel);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    if (!disclaimerAccepted) return;
    const list = Array.from(e.dataTransfer.files ?? []).filter(Boolean);
    if (list.length) ingestClientFiles(list);
  };

  async function submit() {
    setResult(null);
    setGlobalError("");
    setDisclaimerReminder(false);
    setDeliveryBanner("");

    const parts = validateDeliveryForSubmit(delivery);
    if ("invalid" in parts) {
      setFieldErrors({ [parts.field]: parts.message });
      setDeliveryBanner("Revisá tus datos antes de enviar.");
      return;
    }
    setFieldErrors({});

    if (!disclaimerAccepted) {
      setDisclaimerReminder(true);
      setGlobalError("");
      disclaimerScrollRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
      return;
    }

    if (files.length === 0) {
      setGlobalError("Primero elegí o arrastrá tus archivos en el recuadro.");
      return;
    }

    if (accumBytes(files) > CONTRACT_MAX_TOTAL_BYTES) {
      setGlobalError(
        `En conjunto superan los ${Math.round(CONTRACT_MAX_TOTAL_BYTES / (1024 * 1024))} MB máximos. Eliminá algunos archivos.`,
      );
      return;
    }

    const fd = new FormData();
    fd.append("disclaimer_accepted", "true");
    fd.append("disclaimer_acceptance_method", "checkbox");
    fd.append("submission_source", "web");
    fd.append("delivery_channel", parts.delivery_channel);
    if (!("delivery_target_omitted" in parts))
      fd.append("delivery_target", parts.delivery_target);

    files.forEach((f) => {
      fd.append("files", f, f.name);
    });

    setBusy(true);
    setLoadingSession((s) => s + 1);

    try {
      const outcome = await submitContractUploadFlow(fd);
      switch (outcome.outcome) {
        case "error":
          if (outcome.disclaimerRequired) {
            setDisclaimerReminder(true);
            setDisclaimerAccepted(false);
            disclaimerScrollRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });
          }
          setGlobalError(outcome.message);
          return;
        case "success":
          setGlobalError("");
          if (delivery.channel === "web_link" && outcome.publicShortId) {
            const q = outcome.linkExpiresAt
              ? `?expires=${encodeURIComponent(outcome.linkExpiresAt)}`
              : "";
            router.push(`/r/${encodeURIComponent(outcome.publicShortId)}${q}`);
            return;
          }
          setResult({
            kind: "success",
            submissionId: outcome.submissionId,
            hint: outcome.channelSummary,
          });
          return;
        case "not_analyzable":
          setResult({ kind: "reject", reasons: outcome.reasons });
          return;
        default:
          return;
      }
    } catch {
      setGlobalError(
        "Algo interrumpió el envío. Comprobá la conexión y volvé a intentarlo en un momento.",
      );
    } finally {
      setBusy(false);
    }
  }

  const removeAt = (idx: number) => {
    const next = files.filter((_, i) => i !== idx);
    setFiles(next);
    setPhase(next.length ? "selected" : "empty");
  };

  return (
    <div className="flex flex-col gap-6">
      {busy ? <ContractAnalysisLoadingPanel key={loadingSession} /> : null}
      <header className="flex flex-col gap-2">
        <h1
          id={`${baseId}-h1`}
          className="text-xl font-semibold text-text-primary"
        >
          Subí tu contrato
        </h1>
        <p className="text-base leading-relaxed text-text-secondary">
          Podés combinar páginas en PDF y fotos nítidas. Te avisamos en el canal
          que elijas cuando el análisis quede listo.
        </p>
      </header>

      <DeliveryChannelFields
        idPrefix={`${baseId}-dlv`}
        value={delivery}
        fieldErrors={fieldErrors}
        deliveryError={deliveryBanner}
        onChange={(d) => {
          setDelivery(d);
          setFieldErrors({});
          setDeliveryBanner("");
        }}
      />

      <div ref={disclaimerScrollRef}>
        <DisclaimerCallout
          variant="gate"
          accepted={disclaimerAccepted}
          onAcceptedChange={(v) => {
            setDisclaimerAccepted(v);
            if (v) setDisclaimerReminder(false);
          }}
        />
      </div>

      <section
        aria-labelledby={`${baseId}-zone-title`}
        className="flex flex-col gap-3"
      >
        <h2
          id={`${baseId}-zone-title`}
          className="text-base font-semibold text-text-primary"
        >
          Archivos
        </h2>
        {!disclaimerAccepted ? (
          <p className="text-sm leading-relaxed text-text-secondary">
            Marcá la casilla de aviso legal del bloque de arriba para habilitar
            la subida y evitar tratamiento sin tu consentimiento explícito.
          </p>
        ) : null}

        <div
          onDragEnter={(e) => {
            e.preventDefault();
          }}
          onDragOver={(e) => {
            e.preventDefault();
          }}
          onDrop={disclaimerAccepted ? onDrop : undefined}
          aria-disabled={!disclaimerAccepted}
          className={`rounded-[var(--radius-card)] border border-dashed ${
            disclaimerAccepted
              ? "border-border bg-surface"
              : "cursor-not-allowed border-border opacity-55"
          } px-4 py-6`}
        >
          <div className="flex flex-col items-center gap-3 text-center">
            <button
              type="button"
              disabled={!disclaimerAccepted || busy}
              onClick={() => fileInputRef.current?.click()}
              className={`flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] border border-accent bg-accent px-4 py-2 text-base font-semibold text-white transition-opacity hover:opacity-92 disabled:cursor-not-allowed disabled:opacity-40 ${focusBtn}`}
              aria-labelledby={`${baseId}-zone-title`}
              aria-controls={`${baseId}-file-input`}
            >
              Elegí tus archivos
            </button>
            <span className="text-sm text-text-secondary">
              o dejalos caer dentro de este recuadro.
            </span>
            <input
              ref={fileInputRef}
              id={`${baseId}-file-input`}
              type="file"
              multiple
              accept={acceptAttr}
              aria-label="Selector de contrato (PDF e imágenes)"
              disabled={!disclaimerAccepted || busy}
              className="sr-only"
              onChange={onInputChange}
            />
          </div>
        </div>

        <div aria-live="polite">
          <p className="text-xs text-text-secondary">
            Estados: Archivos&nbsp;
            <span>{phase === "empty" ? "vacío" : "seleccionados"}</span>
            {!busy ? null : <> · enviándose</>}
          </p>
        </div>

        {files.length > 0 ? (
          <ul
            className="flex flex-col divide-y divide-border rounded-[var(--radius-input)] border border-border bg-surface"
            aria-label="Archivos listos para enviar"
          >
            {files.map((f, i) => (
              <li
                key={`${f.name}-${f.lastModified}-${i}`}
                className="flex items-start justify-between gap-3 px-3 py-3"
              >
                <span className="min-w-0 flex-1 break-words text-sm text-text-primary">
                  {f.name}
                </span>
                <button
                  type="button"
                  onClick={() => removeAt(i)}
                  className={`min-h-[44px] min-w-[44px] shrink-0 rounded-[var(--radius-input)] px-3 text-sm font-medium text-accent underline-offset-4 hover:underline disabled:opacity-45 ${focusBtn}`}
                  disabled={busy}
                  aria-label={`Quitar archivo ${f.name}`}
                >
                  Quitar
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-secondary">Sin archivos aún.</p>
        )}
      </section>

      <div aria-live="assertive" className="min-h-[2.5rem]">
        {disclaimerReminder ? (
          <p role="alert" className="text-sm font-semibold text-verdict-red">
            Confirmá primero la casilla de aviso legal; sin eso tu envío puede
            ser rechazado por el servidor.
          </p>
        ) : null}
        {globalError ? (
          <p role="alert" className="text-sm font-semibold text-verdict-red">
            {globalError}
          </p>
        ) : null}
      </div>

      {result?.kind === "success" ? (
        <aside
          className="rounded-[var(--radius-card)] border border-verdict-green bg-verdict-green-bg px-4 py-4 shadow-sm"
          role="status"
          aria-labelledby={`${baseId}-ok`}
        >
          <p
            id={`${baseId}-ok`}
            className="text-base font-semibold text-text-primary"
          >
            Recibimos tu envío para analizarlo
          </p>
          <p className="mt-2 text-sm text-text-secondary">
            Seguimos el proceso en segundo plano. Referencia rápida:{" "}
            <span className="font-mono text-xs text-text-primary select-all">
              {result.submissionId}
            </span>
            .
          </p>
          <p className="mt-2 text-sm text-text-secondary">
            Canal elegido: {result.hint}. Si no ves nada, revisá el SMS, filtros
            del correo o abrí el enlace web según cómo lo configuraste.
          </p>
        </aside>
      ) : null}

      {result?.kind === "reject" ? (
        <aside
          className="rounded-[var(--radius-card)] border border-verdict-yellow bg-verdict-yellow-bg px-4 py-4 shadow-sm"
          role="alert"
          aria-labelledby={`${baseId}-rej`}
        >
          <p
            id={`${baseId}-rej`}
            className="text-base font-semibold text-text-primary"
          >
            No pudimos producir tu informe a partir del material que mandaste.
          </p>
          <p className="mt-3 text-sm text-text-secondary">
            Motivos que marcó el servicio para orientarte mejor:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-base text-text-primary">
            {result.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-text-secondary">
            Podés probar fotos más contrastadas y con buena luz o un PDF nuevo
            exportado con texto seleccionable.
          </p>
        </aside>
      ) : null}

      <div className="flex flex-col gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={submit}
          className={`flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-92 disabled:cursor-wait disabled:opacity-65 ${focusBtn}`}
          aria-busy={busy ? true : undefined}
        >
          {busy ? "Enviando tu contrato..." : "Enviar"}
        </button>
        {(result || globalError || files.length) && !busy ? (
          <button
            type="button"
            onClick={() => {
              setResult(null);
              setFiles([]);
              setPhase("empty");
              setGlobalError("");
              setDisclaimerAccepted(false);
              setDelivery(defaultDeliveryDraft());
            }}
            className={`flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-base font-medium text-text-primary ${focusBtn}`}
          >
            Empezar de nuevo
          </button>
        ) : null}
      </div>
    </div>
  );
}

function accumBytes(list: readonly File[]): number {
  let t = 0;
  for (const f of list) t += f.size;
  return t;
}
