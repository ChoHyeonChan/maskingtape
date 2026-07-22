import { describe, expect, it } from "vitest";
import { summarize } from "./summary";
import type { Detection } from "../types/detection";

function d(kind: string): Detection {
  return { kind, start: 0, end: 0, text: "", confidence: 1, detector: "T" };
}

describe("summarize", () => {
  it("returns an empty list for no detections", () => {
    expect(summarize([])).toEqual([]);
  });

  it("counts detections per kind", () => {
    const result = summarize([d("phone"), d("phone"), d("email")]);
    expect(result).toEqual([
      { kind: "phone", count: 2 },
      { kind: "email", count: 1 },
    ]);
  });

  it("orders kinds by KIND_ORDER regardless of input order", () => {
    // 입력은 name→phone→rrn 순이지만 결과는 rrn→phone→name 순이어야 한다
    const result = summarize([d("name"), d("phone"), d("rrn")]);
    expect(result.map((r) => r.kind)).toEqual(["rrn", "phone", "name"]);
  });

  it("appends unknown kinds after the known ones", () => {
    const result = summarize([d("mystery"), d("phone")]);
    expect(result.map((r) => r.kind)).toEqual(["phone", "mystery"]);
  });
});
