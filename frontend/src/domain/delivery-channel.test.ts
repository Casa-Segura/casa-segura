import { describe, expect, it } from "vitest";
import {
  isValidE164Phone,
  isValidEmailFormat,
  validateDeliveryForSubmit,
} from "./delivery-channel";

describe("isValidEmailFormat", () => {
  it("accepts plausible addresses", () => {
    expect(isValidEmailFormat("a@b.co")).toBe(true);
    expect(isValidEmailFormat("user.name@example.com")).toBe(true);
  });
  it("rejects obviously invalid strings", () => {
    expect(isValidEmailFormat("not-an-email")).toBe(false);
    expect(isValidEmailFormat("@nodomain.com")).toBe(false);
  });
});

describe("isValidE164Phone", () => {
  it("requires +country and 10–15 digit length overall", () => {
    expect(isValidE164Phone("+50312345678")).toBe(true); // typical SV (+503 + 8)
    expect(isValidE164Phone("+503123456789")).toBe(true);
    expect(isValidE164Phone("+50312345678901")).toBe(true);
    expect(isValidE164Phone("503123456789")).toBe(false); // missing +
    expect(isValidE164Phone("+0503123456789")).toBe(false); // leading 0 in NSN
    expect(isValidE164Phone("+1234567890123456")).toBe(false); // >15 digits
  });
});

describe("validateDeliveryForSubmit", () => {
  it("omits destination for web_link", () => {
    const r = validateDeliveryForSubmit({
      channel: "web_link",
      email: "",
      phone: "",
    });
    expect(
      "delivery_target_omitted" in r && r.delivery_channel === "web_link",
    ).toBe(true);
  });
  it("rejects invalid email for email_pdf", () => {
    const r = validateDeliveryForSubmit({
      channel: "email_pdf",
      email: "bad",
      phone: "",
    });
    expect("invalid" in r && r.field === "email").toBe(true);
  });
  it("rejects invalid E.164 for sms_summary", () => {
    const r = validateDeliveryForSubmit({
      channel: "sms_summary",
      email: "",
      phone: "+abc",
    });
    expect("invalid" in r && r.field === "phone").toBe(true);
  });
});
