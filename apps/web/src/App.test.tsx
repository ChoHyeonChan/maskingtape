// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

// 탐지 범위·입력·결과 체험은 전부 /demo 페이지로 옮겨갔다(#553 후속) — 랜딩(App)은
// 이제 소개(히어로)와 클로징 CTA만 있는 정적인 마케팅 페이지다. 그 상호작용
// 테스트들은 DemoPage.test.tsx로 옮겼다.
describe("App (landing page)", () => {
  it("renders the hero and closing CTA, both pointing to the /demo page", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /내 정보부터 가려보세요/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /지금 체험하기/ })).toHaveAttribute("href", "/demo");
    expect(screen.getByRole("link", { name: /웹 데모 열기/ })).toHaveAttribute("href", "/demo");
  });

  it("does not render the interactive scan tool or the coverage section — those live on /demo now", () => {
    render(<App />);

    expect(screen.queryByLabelText("탐지할 텍스트 입력")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "탐지 범위" })).not.toBeInTheDocument();
  });

  it("sends the nav help button to /demo, since there is no coachmark on the landing page", () => {
    const originalLocation = window.location;
    // jsdom의 navigation은 assign만 허용하니, href 대입을 가로채려고 location 객체를
    // 통째로 바꿔치기한다 — App.tsx의 goToDemo()가 window.location.href = "/demo"로
    // 이동시키는지 확인하기 위해서다.
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, href: "" },
    });

    render(<App />);
    screen.getByRole("button", { name: "사용 안내 다시 보기" }).click();

    expect(window.location.href).toBe("/demo");

    Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  });
});
