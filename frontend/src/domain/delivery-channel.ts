/** DOMAIN_MODEL §2 / platform_core.enums.DeliveryChannel string values — must match backend. */

export type DeliveryChannel = "email_pdf" | "whatsapp_summary" | "web_link";

export const DELIVERY_CHANNELS: DeliveryChannel[] = [
  "email_pdf",
  "whatsapp_summary",
  "web_link",
];

export type DeliveryDraft = {
  channel: DeliveryChannel;
  email: string;
  whatsappPhone: string;
};

export function defaultDeliveryDraft(): DeliveryDraft {
  return {
    channel: "web_link",
    email: "",
    whatsappPhone: "",
  };
}

/** E.164: + prefix, country code starts 1–9, ≤15 digits total (ITU‑T limit). Mirrors PRD +503 examples. */
export function isValidE164Phone(input: string): boolean {
  const s = input.trim();
  const re = /^\+[1-9]\d{1,14}$/;
  if (!re.test(s)) return false;
  const digits = s.slice(1).length;
  return digits >= 10 && digits <= 15;
}

/** Pragmatic client-side email check; authoritative validation stays on BE. */
export function isValidEmailFormat(email: string): boolean {
  const s = email.trim();
  const re = /^[^\s@]+@[^\s@][^\s.@]*(?:\.[^\s.@]+)+$/;
  return s.length <= 254 && re.test(s);
}

/**
 * Validates draft and builds the subset sent with multipart + Server Actions / CS‑296 JSON body.
 */
export function validateDeliveryForSubmit(
  draft: DeliveryDraft,
): DeliverySubmitParts {
  switch (draft.channel) {
    case "web_link":
      return {
        delivery_channel: "web_link",
        delivery_target_omitted: true,
      };
    case "email_pdf": {
      const email = draft.email.trim();
      if (!isValidEmailFormat(email)) {
        return {
          invalid: true,
          field: "email",
          message:
            "Escribí un correo válido para enviarte el PDF. Revisá erratas antes de enviar.",
        };
      }
      return {
        delivery_channel: "email_pdf",
        delivery_target: email,
      };
    }
    case "whatsapp_summary": {
      const raw = draft.whatsappPhone.trim();
      if (!isValidE164Phone(raw)) {
        return {
          invalid: true,
          field: "phone",
          message:
            "Ingresá tu número en formato internacional E.164, por ejemplo +503XXXXXXX.",
        };
      }
      return {
        delivery_channel: "whatsapp_summary",
        delivery_target: raw,
      };
    }
  }
}

export type DeliverySubmitParts =
  | {
      invalid: true;
      field: "email" | "phone";
      message: string;
    }
  | {
      delivery_channel: "web_link";
      delivery_target_omitted: true;
    }
  | {
      delivery_channel: "email_pdf" | "whatsapp_summary";
      delivery_target: string;
    };
