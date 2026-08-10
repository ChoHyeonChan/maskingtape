import { describe, expect, it } from "vitest";
import { summarize } from "./summary";
import type { Detection } from "../types/detection";

function d(kind: string, confidence = 1): Detection {
  return { kind, start: 0, end: 0, confidence, detector: "T" };
}

describe("summarize", () => {
  it("returns an empty list for no detections", () => {
    expect(summarize([])).toEqual([]);
  });

  it("counts detections per kind", () => {
    const result = summarize([d("phone"), d("phone"), d("email")]);
    expect(result).toEqual([
      { kind: "phone", count: 2, minConfidence: 1 },
      { kind: "email", count: 1, minConfidence: 1 },
    ]);
  });

  it("orders kinds by KIND_ORDER regardless of input order", () => {
    // 입력은 name→phone→rrn 순이지만 결과는 rrn→phone→name 순이어야 한다
    const result = summarize([d("name"), d("phone"), d("rrn")]);
    expect(result.map((r) => r.kind)).toEqual(["rrn", "phone", "name"]);
  });

  it("keeps core business registration detections in the known-kind order", () => {
    const result = summarize([d("biz_reg"), d("phone")]);
    expect(result.map((r) => r.kind)).toEqual(["phone", "biz_reg"]);
  });

  it("appends unknown kinds after the known ones", () => {
    const result = summarize([d("mystery"), d("phone")]);
    expect(result.map((r) => r.kind)).toEqual(["phone", "mystery"]);
  });

  it("tracks the lowest confidence within a kind, not the average (#237)", () => {
    const result = summarize([d("name", 0.9), d("name", 0.5), d("name", 0.75)]);
    expect(result).toEqual([{ kind: "name", count: 3, minConfidence: 0.5 }]);
  });
});
