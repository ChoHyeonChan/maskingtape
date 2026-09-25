// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceIntro } from "./ServiceIntro";

describe("ServiceIntro (#455)", () => {
  it("explains the rule + local LLM hybrid approach without overclaiming pure-browser processing", () => {
    render(<ServiceIntro />);
    const section = screen.getByRole("region", { name: "서비스 소개" });

    expect(section).toHaveTextContent("로컬 LLM");
    // 탐지는 실제로 API 서버를 거치므로("브라우저 안에서만 처리"라고 하면 사실과 다르다),
    // 무엇이 브라우저에 남고 무엇이 서버로 가는지 정확히 구분해 설명해야 한다.
    expect(section).toHaveTextContent("저장·기록하지 않습니다");
  });
});
