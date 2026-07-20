import { describe, expect, it } from "vitest";
import { buildSegments } from "./segments";
import type { Detection } from "../types/detection";

function detection(overrides: Partial<Detection>): Detection {
  return {
    kind: "phone",
    start: 0,
    end: 0,
    text: "",
    confidence: 1,
    detector: "Test",
    ...overrides,
  };
}

describe("buildSegments", () => {
  it("returns a single plain segment when there are no detections", () => {
    const segments = buildSegments("안녕하세요", []);
    expect(segments).toEqual([{ kind: "plain", text: "안녕하세요" }]);
  });

  it("splits plain text around a single detection", () => {
    const text = "연락처 010-1234-5678 입니다";
    const d = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678" });
    const segments = buildSegments(text, [d]);
    expect(segments).toEqual([
      { kind: "plain", text: "연락처 " },
      { kind: "detection", text: "010-1234-5678", detection: d },
      { kind: "plain", text: " 입니다" },
    ]);
  });

  it("handles multiple non-overlapping detections in order", () => {
    const text = "AB010-1234-5678CDtest@example.comEF";
    const phone = detection({ kind: "phone", start: 2, end: 15, text: "010-1234-5678" });
    const email = detection({ kind: "email", start: 17, end: 34, text: "test@example.com" });
    const segments = buildSegments(text, [phone, email]);
    expect(segments.map((s) => s.text).join("")).toBe(text);
    expect(segments.filter((s) => s.kind === "detection")).toHaveLength(2);
  });

  it("keeps the earlier-starting detection when two overlap", () => {
    const text = "0101234567890123";
    const first = detection({ kind: "phone", start: 0, end: 11, text: text.slice(0, 11) });
    const overlapping = detection({ kind: "rrn", start: 5, end: 16, text: text.slice(5, 16) });
    const segments = buildSegments(text, [first, overlapping]);
    const detections = segments.filter((s) => s.kind === "detection");
    expect(detections).toHaveLength(1);
    expect(detections[0]).toMatchObject({ detection: first });
  });

  it("returns no segments for empty input", () => {
    expect(buildSegments("", [])).toEqual([]);
  });
});
