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
});
