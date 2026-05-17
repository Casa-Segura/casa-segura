"use client";

import type { DragEvent } from "react";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { FileArrowUp, Trash } from "@phosphor-icons/react";
import { submitContractUploadFlow } from "@/actions/contract-flow";
import { AnalysisWorkbench } from "@/components/analysis-workbench";
import { ContractAnalysisLoadingPanel } from "@/components/contract-analysis-loading-panel";
import {
  contractFilePreviewKind,
  defaultContractPreviewFileIndex,
} from "@/components/contract-upload-preview.helpers";
import {
  CasaButton,
  DisclaimerPanel,
  FindingCard,
  LegalSummary,
  SkeletonBlock,
  StepPill,
  cx,
  focusRing,
  scanFlowDesktopSplitGridClass,
} from "@/components/casa-ui";
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

const ContractUploadPreview = dynamic(
  () => import("@/components/contract-upload-preview"),
  {
    ssr: false,
    loading: () => (
      <div
        className="flex min-h-[min(50vh,420px)] flex-col justify-center gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)]"
        aria-busy="true"
      >
        <SkeletonBlock className="h-4 w-2/5" label="Cargando vista previa" />
        <SkeletonBlock className="h-48 w-full" label="Cargando documento" />
        <SkeletonBlock className="h-4 w-3/5" label="Cargando vista previa" />
      </div>
    ),
  },
);

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
  const [previewFileIndex, setPreviewFileIndex] = useState(0);

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

  const resolvedPreviewFileIndex = useMemo(() => {
    if (files.length === 0) return 0;
    if (previewFileIndex >= 0 && previewFileIndex < files.length) {
      return previewFileIndex;
    }
    return defaultContractPreviewFileIndex(files);
  }, [files, previewFileIndex]);

  const previewTargetFile =
    busy || files.length === 0
      ? null
      : (files[resolvedPreviewFileIndex] ?? null);

  const previewObjectUrl = useMemo(
    () => (previewTargetFile ? URL.createObjectURL(previewTargetFile) : null),
    [previewTargetFile],
  );

  useEffect(() => {
    return () => {
      if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
    };
  }, [previewObjectUrl]);

  const mesaAssetPreview =
    !busy && previewObjectUrl && previewTargetFile
      ? {
          kind: contractFilePreviewKind(previewTargetFile),
          objectUrl: previewObjectUrl,
          fileName: previewTargetFile.name,
        }
      : null;

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

      const safeFocusedIdx =
        files.length === 0
          ? 0
          : previewFileIndex >= 0 && previewFileIndex < files.length
            ? previewFileIndex
            : defaultContractPreviewFileIndex(files);
      const prevFocused = files[safeFocusedIdx] ?? null;

      next.sort((a, b) => a.name.localeCompare(b.name));
      setFiles(next);
      setPhase(next.length ? "selected" : "empty");
      if (next.length === 0) {
        setPreviewFileIndex(0);
      } else if (prevFocused && next.includes(prevFocused)) {
        setPreviewFileIndex(next.indexOf(prevFocused));
      } else {
        setPreviewFileIndex(defaultContractPreviewFileIndex(next));
      }
      if (!errors.length) setGlobalError("");
    },
    [files, previewFileIndex],
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
    setPreviewFileIndex((pi) => {
      if (next.length === 0) return 0;
      if (idx < pi) return pi - 1;
      if (idx === pi) return Math.min(pi, next.length - 1);
      return pi;
    });
  };

  return (
    <div className={scanFlowDesktopSplitGridClass}>
      {busy ? (
        <div className="lg:hidden">
          <ContractAnalysisLoadingPanel key={loadingSession} />
        </div>
      ) : null}

      <section className="flex flex-col gap-6 self-start rounded-[var(--radius-panel)] border border-border bg-surface p-5 shadow-[var(--shadow-soft)] sm:p-6">
        <header className="flex flex-col gap-3">
          <StepPill>Paso 2 de 4 · Subir contrato</StepPill>
          <div>
            <h1
              id={`${baseId}-h1`}
              className="text-balance text-2xl font-semibold tracking-tight text-text-primary"
            >
              Subí tu contrato
            </h1>
            <p className="mt-2 text-base leading-relaxed text-text-secondary">
              Podés combinar PDF y fotos nítidas. Te avisamos por el canal que
              elijas cuando el análisis quede listo.
            </p>
          </div>
        </header>

        <section
          aria-labelledby={`${baseId}-zone-title`}
          className="flex flex-col gap-3"
        >
          <div className="flex items-center justify-between gap-3">
            <h2
              id={`${baseId}-zone-title`}
              className="text-base font-semibold text-text-primary"
            >
              Archivos
            </h2>
            <span className="rounded-[var(--radius-pill)] bg-surface-muted px-2.5 py-1 text-xs text-text-secondary">
              PDF, JPEG, PNG, HEIC, WEBP
            </span>
          </div>

          <div
            onDragEnter={(e) => {
              e.preventDefault();
            }}
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={disclaimerAccepted ? onDrop : undefined}
            aria-disabled={!disclaimerAccepted}
            className={cx(
              "rounded-[var(--radius-card)] border border-dashed px-4 py-6 transition-[background-color,border-color,opacity] duration-[var(--motion-base)]",
              disclaimerAccepted
                ? "border-border-strong bg-surface-subtle"
                : "cursor-not-allowed border-border bg-surface-muted/70 opacity-70",
            )}
          >
            <div className="flex flex-col items-center gap-4 text-center">
              <span className="inline-flex size-12 items-center justify-center rounded-full bg-accent-light text-accent">
                <FileArrowUp size={24} aria-hidden />
              </span>
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  Arrastrá el archivo o elegilo desde tu dispositivo
                </p>
                <p className="mt-1 text-sm leading-relaxed text-text-secondary">
                  Máximo 15 MB por archivo. La lectura funciona mejor con texto
                  seleccionable o fotos bien iluminadas.
                </p>
              </div>
              <CasaButton
                disabled={!disclaimerAccepted || busy}
                onClick={() => fileInputRef.current?.click()}
                className="w-full"
                aria-labelledby={`${baseId}-zone-title`}
                aria-controls={`${baseId}-file-input`}
              >
                Seleccionar archivos
              </CasaButton>
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

          {!disclaimerAccepted ? (
            <p className="text-sm leading-relaxed text-text-secondary">
              Aceptá el aviso legal para habilitar la subida y confirmar el
              tratamiento del documento.
            </p>
          ) : null}

          <div aria-live="polite">
            <p className="text-xs text-text-secondary">
              Estado: archivos{" "}
              <span>{phase === "empty" ? "sin seleccionar" : "listos"}</span>
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
                  className={cx(
                    "flex flex-wrap items-start justify-between gap-2 px-3 py-3 transition-colors duration-[var(--motion-fast)]",
                    resolvedPreviewFileIndex === i
                      ? "bg-accent-light/40 ring-2 ring-accent/20 ring-inset"
                      : "",
                  )}
                >
                  <span className="min-w-0 flex-1 basis-[min(100%,220px)] break-words text-sm text-text-primary">
                    {f.name}
                  </span>
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setPreviewFileIndex(i)}
                      disabled={busy}
                      aria-current={
                        resolvedPreviewFileIndex === i ? "true" : undefined
                      }
                      className={cx(
                        "inline-flex min-h-[44px] items-center rounded-[var(--radius-input)] px-3 text-sm font-semibold text-accent transition-[background-color,transform] duration-[var(--motion-fast)] hover:bg-accent-light active:translate-y-px disabled:opacity-45",
                        focusRing,
                      )}
                    >
                      Vista previa
                    </button>
                    <button
                      type="button"
                      onClick={() => removeAt(i)}
                      className={`inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-[var(--radius-input)] text-accent transition-[background-color,transform] duration-[var(--motion-fast)] hover:bg-accent-light active:translate-y-px disabled:opacity-45 ${focusRing}`}
                      disabled={busy}
                      aria-label={`Quitar archivo ${f.name}`}
                    >
                      <Trash size={18} aria-hidden />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}

          {!busy && previewObjectUrl && files.length > 0 ? (
            <ContractUploadPreview
              key={previewObjectUrl}
              kind={contractFilePreviewKind(
                files[resolvedPreviewFileIndex]!,
              )}
              objectUrl={previewObjectUrl}
              fileName={
                files[resolvedPreviewFileIndex]!.name
              }
            />
          ) : null}
        </section>

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

        {(disclaimerReminder || globalError) ? (
          <div aria-live="assertive" className="flex flex-col gap-2">
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
        ) : null}

        {result?.kind === "success" ? (
          <DisclaimerPanel tone="green">
            <p
              id={`${baseId}-ok`}
              className="text-base font-semibold text-text-primary"
            >
              Recibimos tu envío para analizarlo
            </p>
            <p className="mt-2 text-sm text-text-secondary">
              Referencia rápida:{" "}
              <span className="select-all font-mono text-xs text-text-primary">
                {result.submissionId}
              </span>
              .
            </p>
            <p className="mt-2 text-sm text-text-secondary">
              Canal elegido: {result.hint}
            </p>
          </DisclaimerPanel>
        ) : null}

        {result?.kind === "reject" ? (
          <div role="alert" className="flex flex-col gap-3">
            <FindingCard
              tone="yellow"
              title="No pudimos producir tu informe"
              body="El material no alcanzó la calidad mínima para un análisis confiable. Probá con fotos más contrastadas o un PDF con texto seleccionable."
            />
            <LegalSummary title="Motivos detectados">
              <ul className="list-disc space-y-2 pl-5">
                {result.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </LegalSummary>
          </div>
        ) : null}

        <div className="flex flex-col gap-3 border-t border-border pt-5">
          <CasaButton
            disabled={busy}
            onClick={submit}
            className="w-full"
            aria-busy={busy ? true : undefined}
          >
            {busy ? "Enviando tu contrato…" : "Enviar análisis"}
          </CasaButton>
          {(result || globalError || files.length) && !busy ? (
            <CasaButton
              variant="secondary"
              onClick={() => {
                setResult(null);
                setFiles([]);
                setPreviewFileIndex(0);
                setPhase("empty");
                setGlobalError("");
                setDisclaimerAccepted(false);
                setDelivery(defaultDeliveryDraft());
              }}
              className="w-full"
            >
              Empezar de nuevo
            </CasaButton>
          ) : null}
        </div>
      </section>

      <AnalysisWorkbench
        mode={busy ? "loading" : result?.kind === "success" ? "complete" : "preview"}
        publicShortId={result?.kind === "success" ? result.submissionId : undefined}
        assetPreview={mesaAssetPreview ?? undefined}
      />
    </div>
  );
}

function accumBytes(list: readonly File[]): number {
  let t = 0;
  for (const f of list) t += f.size;
  return t;
}
