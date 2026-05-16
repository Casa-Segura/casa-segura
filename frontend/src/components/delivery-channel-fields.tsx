import type {
  DeliveryChannel,
  DeliveryDraft,
  DeliverySubmitParts,
} from "@/domain/delivery-channel";

const LABEL_BY_CHANNEL: Record<DeliveryChannel, string> = {
  sms_summary: "Te mandaré un SMS breve con el resultado y el enlace.",
  email_pdf: "Te enviaré por email un PDF descargable con el resultado.",
  web_link: "Te daré un enlace web para revisar aquí mismo (caduca en tiempo).",
};

const SUBLABEL_BY_CHANNEL: Record<DeliveryChannel, string> = {
  sms_summary: "Usamos tu número sólo para este envío.",
  email_pdf: "Necesitamos tu dirección para el envío.",
  web_link: "No hace falta correo ni teléfono en este momento.",
};

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

type Props = {
  idPrefix: string;
  value: DeliveryDraft;
  deliveryError?: string | undefined;
  fieldErrors: Partial<Record<"email" | "phone", string>>;
  onChange(next: DeliveryDraft): void;
  onBlurField?(field: "email" | "phone"): void;
};

export function DeliveryChannelFields(props: Props) {
  const { idPrefix, value, deliveryError, fieldErrors, onChange } = props;
  const groupName = `${idPrefix}-delivery-channel`;

  function setChannel(c: DeliveryChannel) {
    onChange({
      ...value,
      channel: c,
      ...(c !== "email_pdf" ? { email: "" } : {}),
      ...(c !== "sms_summary" ? { phone: "" } : {}),
    });
  }

  return (
    <fieldset className="flex flex-col gap-4 rounded-[var(--radius-input)] border-0 p-0">
      <legend className="sr-only">¿Cómo querés recibir el resultado?</legend>
      <div>
        <h2
          id={`${idPrefix}-delivery-heading`}
          className="text-lg font-semibold text-text-primary"
        >
          ¿Cómo te envío el resultado?
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-text-secondary">
          Elegí uno. Para SMS o email usaremos el dato sólo para entregarte el
          informe.
        </p>
      </div>
      <div
        role="radiogroup"
        aria-labelledby={`${idPrefix}-delivery-heading`}
        className="flex flex-col gap-2"
      >
        {(Object.keys(LABEL_BY_CHANNEL) as DeliveryChannel[]).map((ch) => {
          const cid = `${idPrefix}-ch-${ch}`;
          const selected = value.channel === ch;
          return (
            <label
              key={ch}
              htmlFor={cid}
              className={`flex min-h-[44px] cursor-pointer flex-col rounded-[var(--radius-input)] border px-4 py-3 transition-colors touch-manipulation ${focusRing} ${
                selected
                  ? "border-accent bg-accent-light"
                  : "border-border bg-surface hover:bg-bg"
              }`}
            >
              <span className="flex items-start gap-3">
                <input
                  id={cid}
                  type="radio"
                  name={groupName}
                  value={ch}
                  checked={selected}
                  className={`mt-1 size-5 shrink-0 accent-accent ${focusRing}`}
                  aria-describedby={`${cid}-help`}
                  onChange={() => {
                    setChannel(ch);
                  }}
                />
                <span className="min-w-0 flex-1 text-base leading-snug text-text-primary">
                  <span className="font-medium">
                    {ch === "sms_summary"
                      ? "SMS (resumen)"
                      : ch === "email_pdf"
                        ? "Correo (PDF)"
                        : "Sólo enlace web"}
                  </span>
                  <span className="mt-1 block text-sm font-normal text-text-secondary">
                    {LABEL_BY_CHANNEL[ch]}
                  </span>
                </span>
              </span>
              <span id={`${cid}-help`} className="sr-only">
                {SUBLABEL_BY_CHANNEL[ch]}
              </span>
            </label>
          );
        })}
      </div>

      <div aria-live="polite" className="min-h-[1rem]">
        {deliveryError ? (
          <p role="alert" className="text-sm font-medium text-verdict-red">
            {deliveryError}
          </p>
        ) : null}
      </div>

      {value.channel === "email_pdf" ? (
        <div className="flex flex-col gap-2">
          <label
            htmlFor={`${idPrefix}-email`}
            className="text-sm font-medium text-text-primary"
          >
            Tu correo
          </label>
          <input
            id={`${idPrefix}-email`}
            type="email"
            name="delivery_email"
            inputMode="email"
            autoComplete="email"
            value={value.email}
            aria-invalid={fieldErrors.email ? true : undefined}
            aria-describedby={
              fieldErrors.email ? `${idPrefix}-email-err` : undefined
            }
            onChange={(e) => onChange({ ...value, email: e.target.value })}
            onBlur={() => props.onBlurField?.("email")}
            className={`min-h-[44px] rounded-[var(--radius-input)] border border-border px-4 py-2 text-base text-text-primary outline-none placeholder:text-text-secondary ${focusRing}`}
            placeholder="correo@ejemplo.com"
          />
          {fieldErrors.email ? (
            <p
              role="alert"
              id={`${idPrefix}-email-err`}
              className="text-sm text-verdict-red"
            >
              {fieldErrors.email}
            </p>
          ) : (
            <p className="text-xs text-text-secondary">
              Envío transaccional sólo relacionado con tu análisis.
            </p>
          )}
        </div>
      ) : null}

      {value.channel === "sms_summary" ? (
        <div className="flex flex-col gap-2">
          <label
            htmlFor={`${idPrefix}-phone`}
            className="text-sm font-medium text-text-primary"
          >
            Tu teléfono (E.164)
          </label>
          <input
            id={`${idPrefix}-phone`}
            type="tel"
            name="delivery_phone"
            inputMode="tel"
            autoComplete="tel"
            value={value.phone}
            aria-invalid={fieldErrors.phone ? true : undefined}
            aria-describedby={
              fieldErrors.phone ? `${idPrefix}-phone-err` : undefined
            }
            onChange={(e) =>
              onChange({ ...value, phone: e.target.value })
            }
            onBlur={() => props.onBlurField?.("phone")}
            className={`min-h-[44px] rounded-[var(--radius-input)] border border-border px-4 py-2 text-base font-mono text-text-primary outline-none placeholder:text-text-secondary ${focusRing}`}
            placeholder="+503XXXXXXXX"
          />
          {fieldErrors.phone ? (
            <p
              role="alert"
              id={`${idPrefix}-phone-err`}
              className="text-sm text-verdict-red"
            >
              {fieldErrors.phone}
            </p>
          ) : (
            <p className="text-xs text-text-secondary">
              Incluye el prefijo país con +. Ejemplo: +503XXXXXXXX.
            </p>
          )}
        </div>
      ) : null}
    </fieldset>
  );
}

export function summarizeDelivery(
  parts: Exclude<DeliverySubmitParts, { invalid: true }>,
): string {
  if ("delivery_target_omitted" in parts) return "Enlace web";
  return parts.delivery_channel === "sms_summary" ? "SMS" : "PDF al correo";
}
