// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccuracyPage } from "./AccuracyPage";

describe("AccuracyPage", () => {
  it("shows the overall F1 score and the plain-language translation of it", () => {
    render(<AccuracyPage />);

    expect(screen.getByText("전체 F1 점수")).toBeInTheDocument();
    // README 「정확도」 표 전체 행(F1 0.987, 재현율 0.987, 2026-10-26 main `2802949` 재측정 #739)과 같은 값이다(#499, #731).
    expect(screen.getByText("98.7")).toBeInTheDocument();
    expect(screen.getByText(/개인정보 100개 중 약 99개를 찾아 가려요\(재현율 0\.987\)/)).toBeInTheDocument();
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
    expect(table).toHaveTextContent("재현율 0.966 · F1 0.967");
    expect(table).toHaveTextContent("문서 5종 조정용");
    expect(table).toHaveTextContent("재현율 0.979 · F1 0.984");
    expect(table).toHaveTextContent("재현율 0.981 · F1 0.958");
    // 규칙을 고칠 때 보지 않은 보고용 세트(#456)를 함께 보여야 조정용 숫자를 실력으로 오해하지 않는다.
    expect(table).toHaveTextContent("문서 5종 보고용");
    expect(table).toHaveTextContent("재현율 0.567 · F1 0.687");
    expect(table).toHaveTextContent("재현율 0.971~0.973 · F1 0.918~0.919");
    expect(table).toHaveTextContent("재현율 0.819 · F1 0.593");
    expect(table).toHaveTextContent("정밀도 0.465");
    // #683은 비용 계산·팀장 승인 전이라 측정을 시작하지 않았다 — 「재는 중」이라고 쓰지 않는다(#731).
    expect(screen.getByText(/웹 데모의 하이브리드는 OpenAI 판단기를 씁니다/)).toHaveTextContent("아직 재지 않았습니다(#683)");
    expect(screen.queryByText(/재는 중/)).not.toBeInTheDocument();
    expect(screen.queryByText(/0\.923/)).not.toBeInTheDocument();
  });

  it("describes the LLM step as re-reading the whole text, not only ambiguous names (#731)", () => {
    render(<AccuracyPage />);

    expect(screen.getByText("로컬 LLM이 글 전체를 다시 읽기")).toBeInTheDocument();
    expect(screen.queryByText(/애매한 이름만/)).not.toBeInTheDocument();
  });

  it("says where each number was measured instead of crediting every table to the 500-doc synthetic set (#731)", () => {
    render(<AccuracyPage />);

    const footnote = screen.getByText(/맨 위 전체 점수와 종류별 막대는/);
    expect(footnote).toHaveTextContent("자체 합성 데이터셋(500건, 규칙 전용 모드)");
    expect(footnote).toHaveTextContent("이름 표는 표마다 데이터가 다릅니다");
    expect(footnote).toHaveTextContent("KDPII");
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
