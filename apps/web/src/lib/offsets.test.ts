// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import type { Detection } from "../types/detection";
import { applyMasking } from "./masking";
import { toUtf16Offsets } from "./offsets";

const EMOJI = "😀";
const EXT_B = String.fromCodePoint(0x20000); // 확장 B 한자 — JS에서 두 칸

/** 서버(파이썬)가 주는 모양 그대로: 위치는 코드포인트 기준이다. */
function serverDetection(text: string, value: string, kind: string): Detection {
  const start = Array.from(text.slice(0, text.indexOf(value))).length;
  return { kind, start, end: start + Array.from(value).length, confidence: 1, detector: "test" };
}

/** 서버 /anonymize(mask)와 같은 결과: 값의 글자 수만큼 별표. */
function serverMasked(text: string, values: string[]): string {
  return values.reduce((out, value) => out.replace(value, "*".repeat(Array.from(value).length)), text);
}

describe("toUtf16Offsets (#495)", () => {
  it("returns the same detections when there is no two-unit character", () => {
    const text = "주민번호 800101-1234560";
    const detections = [serverDetection(text, "800101-1234560", "rrn")];
    expect(toUtf16Offsets(text, detections)).toBe(detections);
  });

  it("shifts positions by one unit per emoji before the value", () => {
    const text = `${EMOJI} 주민번호 800101-1234560`;
    const [converted] = toUtf16Offsets(text, [serverDetection(text, "800101-1234560", "rrn")]);
    expect(text.slice(converted.start, converted.end)).toBe("800101-1234560");
  });

  it("clamps positions beyond the text to its end", () => {
    const text = `${EMOJI}abc`;
    const [converted] = toUtf16Offsets(text, [{ kind: "x", start: 1, end: 99, confidence: 1, detector: "t" }]);
    expect([converted.start, converted.end]).toEqual([2, text.length]);
  });
});

describe("web masking matches the server when wide characters come first (#495)", () => {
  const cases: { name: string; text: string; values: [string, string][] }[] = [
    { name: "emoji x1", text: `${EMOJI} 주민번호 800101-1234560`, values: [["800101-1234560", "rrn"]] },
    {
      name: "emoji x3 + phone",
      text: `좋아요${EMOJI.repeat(3)} 연락처 010-1234-5678입니다`,
      values: [["010-1234-5678", "phone"]],
    },
    { name: "emoji x14", text: `${EMOJI.repeat(14)} 주민번호 800101-1234560`, values: [["800101-1234560", "rrn"]] },
    {
      name: "extension B x4 + phone + email",
      text: `${EXT_B.repeat(4)} 전화 010-1234-5678 메일 hong@example.com`,
      values: [
        ["010-1234-5678", "phone"],
        ["hong@example.com", "email"],
      ],
    },
  ];

  for (const { name, text, values } of cases) {
    it(name, () => {
      const detections = toUtf16Offsets(
        text,
        values.map(([value, kind]) => serverDetection(text, value, kind)),
      );
      const masked = applyMasking(text, detections, "mask");
      expect(masked).toBe(serverMasked(text, values.map(([value]) => value)));
      for (const [value] of values) expect(masked).not.toContain(value.slice(-2));
    });
  }

  it("counts an emoji inside the value as one star, like the server", () => {
    const text = `메모 a${EMOJI}b 끝`;
    const detections = toUtf16Offsets(text, [serverDetection(text, `a${EMOJI}b`, "name")]);
    expect(applyMasking(text, detections, "mask")).toBe("메모 *** 끝");
  });
});
