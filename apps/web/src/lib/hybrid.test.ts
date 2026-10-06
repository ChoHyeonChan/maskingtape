// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { hybridFailureMessage, hybridFellBack, isLlmDetection, readModeInfo } from "./hybrid";

describe("readModeInfo (#547)", () => {
  it("treats a rule request as rule with no failure", () => {
    const info = readModeInfo("rule", { mode_used: "rule", hybrid_failed: false, hybrid_failure_code: null });
    expect(info).toEqual({ requested: "rule", used: "rule", failureCode: null });
    expect(hybridFellBack(info)).toBe(false);
  });

  it("reports a successful hybrid run", () => {
    const info = readModeInfo("hybrid", { mode_used: "hybrid", hybrid_failed: false, hybrid_failure_code: null });
    expect(hybridFellBack(info)).toBe(false);
  });

  it("reports a hybrid request that the server answered with rule results as a fallback, keeping the code", () => {
    const info = readModeInfo("hybrid", { mode_used: "rule", hybrid_failed: true, hybrid_failure_code: "timeout" });
    expect(info).toEqual({ requested: "hybrid", used: "rule", failureCode: "timeout" });
    expect(hybridFellBack(info)).toBe(true);
  });

  it("treats a response without mode fields (older server) as rule, so a hybrid request shows as a fallback", () => {
    const info = readModeInfo("hybrid", {});
    expect(hybridFellBack(info)).toBe(true);
    expect(info.failureCode).toBeNull();
  });
});

describe("hybridFailureMessage", () => {
  it("explains known failure codes and falls back to a generic message", () => {
    expect(hybridFailureMessage("name_judge_unavailable")).toContain("연결돼 있지 않습니다");
    expect(hybridFailureMessage("input_too_long")).toContain("5,000자");
    expect(hybridFailureMessage("spend_limit")).toContain("사용 한도");
    expect(hybridFailureMessage("bad_schema")).toBe("판단기 응답을 처리하지 못했습니다.");
    expect(hybridFailureMessage(null)).toBe("판단기 응답을 처리하지 못했습니다.");
  });
});

describe("isLlmDetection", () => {
  it("recognizes names found by the OpenAI judge, not rule detectors", () => {
    const base = { kind: "name", start: 0, end: 3, confidence: 0.9 };
    expect(isLlmDetection({ ...base, detector: "OpenAINameJudge" })).toBe(true);
    expect(isLlmDetection({ ...base, detector: "NameDetector" })).toBe(false);
  });
});
