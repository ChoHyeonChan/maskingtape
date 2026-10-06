// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccuracyPage } from "./AccuracyPage";

describe("AccuracyPage", () => {
  it("shows the overall F1 score and the plain-language translation of it", () => {
    render(<AccuracyPage />);

    expect(screen.getByText("전체 F1 점수")).toBeInTheDocument();
    expect(screen.getByText(/100건 중 약 97건을 정확히 처리해요/)).toBeInTheDocument();
  });

  it("lists all 10 perfect-score kinds plus a separate 이름 card, matching AccuracySection's real numbers", () => {
    render(<AccuracyPage />);

    for (const label of [
      "주민등록번호",
      "전화번호",
      "이메일",
      "주소",
      "신용카드번호",
      "사업자등록번호",
      "여권번호",
      "계좌번호",
      "생년월일",
      "운전면허번호",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    expect(screen.getAllByText("100%")).toHaveLength(10);
  });

  it("shows the 이름 results table with README's current numbers, including the external KDPII set (#499)", () => {
    render(<AccuracyPage />);

    const table = screen.getByRole("table");
    expect(table).toHaveTextContent("재현율 0.932 · F1 0.949");
    expect(table).toHaveTextContent("재현율 0.899 · F1 0.916");
    expect(table).toHaveTextContent("재현율 0.825 · F1 0.600");
    expect(table).toHaveTextContent("정밀도 0.471");
    expect(screen.getByText(/웹 데모의 하이브리드는 OpenAI 판단기를 씁니다/)).toBeInTheDocument();
    expect(screen.queryByText(/0\.923/)).not.toBeInTheDocument();
  });

  it("explains precision, recall and F1 in plain language", () => {
    render(<AccuracyPage />);

    expect(screen.getByText("정밀도 (Precision)")).toBeInTheDocument();
    expect(screen.getByText("재현율 (Recall)")).toBeInTheDocument();
    expect(screen.getByText("F1 점수")).toBeInTheDocument();
  });

  it("renders the nav with 정확도 marked as the current page", () => {
    render(<AccuracyPage />);

    const link = screen.getByRole("link", { name: "정확도" });
    expect(link).toHaveAttribute("href", "/accuracy");
    expect(link.className).toContain("site-nav__link--active");
  });
});
