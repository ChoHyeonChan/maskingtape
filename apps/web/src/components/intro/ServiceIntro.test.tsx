// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceIntro } from "./ServiceIntro";

describe("ServiceIntro (#455)", () => {
  // 서버 전송·무저장 원칙 고지는 App.test.tsx의 privacy-note(#154, #499)가 이미
  // 검증한다 — ServiceIntro에는 더 이상 중복해서 두지 않는다.
  it("links the primary CTA to the demo section and the download button to GitHub Releases", () => {
    render(<ServiceIntro />);

    expect(screen.getByRole("link", { name: /지금 체험하기/ })).toHaveAttribute("href", "#demo");
    expect(screen.getByRole("link", { name: /다운로드/ })).toHaveAttribute(
      "href",
      "https://github.com/ChoHyeonChan/maskingtape/releases",
    );
  });
});
