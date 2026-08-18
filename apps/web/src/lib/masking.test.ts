import { describe, expect, it } from "vitest";
import { applyMasking } from "./masking";
import type { Detection } from "../types/detection";

function detection(overrides: Partial<Detection>): Detection {
  return { kind: "phone", start: 0, end: 0, confidence: 1, detector: "T", ...overrides };
}

describe("applyMasking (#277)", () => {
  it("returns the original text untouched when there are no detections", () => {
    expect(applyMasking("안녕하세요", [], "mask")).toBe("안녕하세요");
    expect(applyMasking("안녕하세요", [], "label")).toBe("안녕하세요");
  });

  it("replaces detected spans with asterisks in mask mode, preserving length", () => {
    const d = detection({ kind: "phone", start: 4, end: 17 });
    const result = applyMasking("연락처 010-1234-5678 입니다", [d], "mask");
    expect(result).toBe("연락처 ************* 입니다");
  });

  it("replaces detected spans with a [종류] label in label mode", () => {
    const d = detection({ kind: "phone", start: 4, end: 17 });
    const result = applyMasking("연락처 010-1234-5678 입니다", [d], "label");
    expect(result).toBe("연락처 [전화번호] 입니다");
  });

  it("falls back to the raw kind string when there is no Korean label mapping", () => {
    const d = detection({ kind: "unmapped_kind", start: 3, end: 16 });
    const result = applyMasking("면허 110-1234-5678 입니다", [d], "label");
    expect(result).toBe("면허 [unmapped_kind] 입니다");
  });

  it("labels account, birth_date, and driver_license in Korean, not the raw kind string (#282 web-side counterpart, #267)", () => {
    const account = detection({ kind: "account", start: 3, end: 16 });
    expect(applyMasking("계좌 110-1234-5678 입니다", [account], "label")).toBe("계좌 [계좌번호] 입니다");

    const birthDate = detection({ kind: "birth_date", start: 6, end: 16 });
    expect(applyMasking("생년월일은 1999-07-21입니다", [birthDate], "label")).toBe("생년월일은 [생년월일]입니다");

    const driverLicense = detection({ kind: "driver_license", start: 3, end: 15 });
    expect(applyMasking("면허 111234567890 입니다", [driverLicense], "label")).toBe("면허 [운전면허] 입니다");
  });

  it("handles multiple detections and skips overlapping ones the same way regardless of mode", () => {
    const phone = detection({ kind: "phone", start: 3, end: 16 });
    const email = detection({ kind: "email", start: 19, end: 35 });
    const text = "문의 010-1234-5678 / hong@example.com";

    expect(applyMasking(text, [phone, email], "mask")).toBe("문의 ************* / ****************");
    expect(applyMasking(text, [phone, email], "label")).toBe("문의 [전화번호] / [이메일]");
  });
});
