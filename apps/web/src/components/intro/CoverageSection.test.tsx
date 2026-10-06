// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CoverageSection } from "./CoverageSection";

describe("CoverageSection (#455)", () => {
  it("lists all 11 kinds core supports, matching README's 지원 범위와 한계 표", () => {
    render(<CoverageSection />);

    const list = screen.getByRole("list");
    const items = list.querySelectorAll("li");
    expect(items).toHaveLength(11);

    for (const label of [
      "주민등록번호",
      "전화번호",
      "이메일",
      "주소",
      "카드번호",
      "계좌번호",
      "사업자등록번호",
      "여권번호",
      "생년월일",
      "운전면허",
      "이름",
    ]) {
      expect(list).toHaveTextContent(label);
    }
  });

  it("shows README's current numbers: overall F1 0.981 and name recall 0.825 on external data (#499)", () => {
    render(<CoverageSection />);

    expect(screen.getByText("0.981")).toBeInTheDocument();
    expect(screen.getByText("전체 F1 (11종, 규칙 전용)")).toBeInTheDocument();
    expect(screen.getByText("0.825")).toBeInTheDocument();
    expect(screen.getByText("이름 재현율 (외부 대화 데이터, 로컬 LLM)")).toBeInTheDocument();
    expect(screen.queryByText(/하이브리드로 11종/)).not.toBeInTheDocument();
  });
});
