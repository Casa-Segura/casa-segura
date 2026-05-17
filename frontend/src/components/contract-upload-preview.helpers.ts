export function contractFilePreviewKind(file: File): "pdf" | "image" {
  if (file.type === "application/pdf") return "pdf";
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot + 1).toLowerCase() : "";
  if (ext === "pdf") return "pdf";
  return "image";
}

/** Prefer first PDF in the list so preview matches likely primary doc. */
export function defaultContractPreviewFileIndex(files: readonly File[]): number {
  const pdfIdx = files.findIndex(
    (f) =>
      f.type === "application/pdf" ||
      f.name.toLowerCase().endsWith(".pdf"),
  );
  return pdfIdx >= 0 ? pdfIdx : 0;
}

export type ContractUploadPreviewProps = {
  kind: "pdf" | "image";
  objectUrl: string;
  fileName: string;
  density?: "comfortable" | "compact";
  /** Fill lg mesa column; scroll inside, no viewport-based max-height */
  fillParent?: boolean;
  className?: string;
};
