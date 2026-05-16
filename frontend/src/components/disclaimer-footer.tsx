import { DISCLAIMER_LEGAL_SHORT } from "@/legal/disclaimer";

export function DisclaimerFooter() {
  return (
    <p className="text-center text-sm leading-snug text-text-secondary">
      <span className="font-medium text-text-primary">
        {DISCLAIMER_LEGAL_SHORT}
      </span>
      . Casa Segura te ayuda a entender puntos comunes en contratos
      inmobiliarios; no sustituye la revisión de un abogado.
    </p>
  );
}
