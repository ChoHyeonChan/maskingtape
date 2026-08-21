import { describe, expect, it } from "vitest";
import { buildSegments } from "./segments";
import { applyMasking } from "./masking";
import type { Detection } from "../types/detection";

function detection(overrides: Partial<Detection>): Detection {
  return {
    kind: "phone",
    start: 0,
    end: 0,
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
    const d = detection({ kind: "phone", start: 4, end: 17 });
    const segments = buildSegments(text, [d]);
    expect(segments).toEqual([
      { kind: "plain", text: "연락처 " },
      { kind: "detection", text: "010-1234-5678", detection: d },
      { kind: "plain", text: " 입니다" },
    ]);
  });

  it("handles multiple non-overlapping detections in order", () => {
    const text = "AB010-1234-5678CDtest@example.comEF";
    const phone = detection({ kind: "phone", start: 2, end: 15 });
    const email = detection({ kind: "email", start: 17, end: 34 });
    const segments = buildSegments(text, [phone, email]);
    expect(segments.map((s) => s.text).join("")).toBe(text);
    expect(segments.filter((s) => s.kind === "detection")).toHaveLength(2);
  });

  it("keeps the earlier-starting detection when two overlap", () => {
    const text = "0101234567890123";
    const first = detection({ kind: "phone", start: 0, end: 11 });
    const overlapping = detection({ kind: "rrn", start: 5, end: 16 });
    const segments = buildSegments(text, [first, overlapping]);
    const detections = segments.filter((s) => s.kind === "detection");
    expect(detections).toHaveLength(1);
    expect(detections[0]).toMatchObject({ detection: first });
  });

  it("returns no segments for empty input", () => {
    expect(buildSegments("", [])).toEqual([]);
  });

  it("agrees with applyMasking() on which detection wins when two share the same start (#264 follow-up)", () => {
    // 시작 위치가 같은 두 탐지가 겹칠 때, 하이라이트 미리보기(buildSegments)와 실제 내보내는
    // 마스킹 결과(applyMasking)가 서로 다른 탐지를 고르면 화면에서 검토한 내용과 복사·다운로드
    // 되는 결과가 어긋난다. 둘 다 "더 긴 쪽"을 고르는지 확인한다.
    const text = "0123456789012345";
    const shorter = detection({ kind: "phone", start: 0, end: 5 });
    const longer = detection({ kind: "driver_license", start: 0, end: 12 });

    const segments = buildSegments(text, [shorter, longer]);
    const highlighted = segments.filter((s) => s.kind === "detection");
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0]).toMatchObject({ detection: longer });

    const masked = applyMasking(text, [shorter, longer], "label");
    expect(masked).toBe("[운전면허]2345");
  });
});
