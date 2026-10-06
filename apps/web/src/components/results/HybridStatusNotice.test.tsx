// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HybridStatusNotice } from "./HybridStatusNotice";

const ruleName = { kind: "name", start: 0, end: 3, confidence: 1, detector: "NameDetector" };
const llmName = { kind: "name", start: 5, end: 8, confidence: 0.9, detector: "OpenAINameJudge" };

describe("HybridStatusNotice (#547)", () => {
  it("renders nothing for a rule-only scan", () => {
    const { container } = render(
      <HybridStatusNotice modeInfo={{ requested: "rule", used: "rule", failureCode: null }} detections={[ruleName]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("alerts that hybrid failed and shows the reason when the server fell back to rule results", () => {
    render(
      <HybridStatusNotice
        modeInfo={{ requested: "hybrid", used: "rule", failureCode: "name_judge_unavailable" }}
        detections={[ruleName]}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("하이브리드 판단에 실패해 규칙 전용 결과만 보여 줍니다");
    expect(alert).toHaveTextContent("하이브리드 판단기가 연결돼 있지 않습니다");
  });

  it("counts the names the OpenAI judge added on a successful hybrid run", () => {
    render(
      <HybridStatusNotice
        modeInfo={{ requested: "hybrid", used: "hybrid", failureCode: null }}
        detections={[ruleName, llmName]}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("규칙이 놓친 이름 1건을 더 찾았습니다");
  });

  it("says no extra names were found when the judge added none", () => {
    render(
      <HybridStatusNotice modeInfo={{ requested: "hybrid", used: "hybrid", failureCode: null }} detections={[ruleName]} />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("더 찾은 이름은 없습니다");
  });
});
