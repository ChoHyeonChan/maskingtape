// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

// 입력·결과 체험만 /demo 페이지로 옮겨갔다(#553 후속) — 탐지 범위(무엇을 잡나요)는
// 랜딩에 있다. 랜딩(App)은 이제 소개(히어로)+탐지 범위+클로징 CTA로 된 정적인
// 마케팅 페이지다. 입력·결과 체험 관련 테스트들은 DemoPage.test.tsx에 있다.
describe("App (landing page)", () => {
  it("renders the hero and closing CTA, both pointing to the /demo page", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /내 정보부터 가려보세요/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /지금 체험하기/ })).toHaveAttribute("href", "/demo");
    expect(screen.getByRole("link", { name: /웹 데모 열기/ })).toHaveAttribute("href", "/demo");
  });

  it("renders the coverage section listing all 11 kinds", () => {
    render(<App />);

    expect(screen.getByRole("region", { name: "탐지 범위" })).toHaveTextContent("이름");
  });

  it("does not render the interactive scan tool or the nav help button", () => {
    render(<App />);

    expect(screen.queryByLabelText("탐지할 텍스트 입력")).not.toBeInTheDocument();
    // 도움말 버튼(코치마크 안내)은 /demo 페이지에만 있다 — 여기엔 안내할 코치마크가 없다.
    expect(screen.queryByRole("button", { name: "사용 안내 다시 보기" })).not.toBeInTheDocument();
  });
});
