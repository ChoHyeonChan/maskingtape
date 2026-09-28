// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MaskPreview } from "./MaskPreview";

describe("MaskPreview (#455 hero visual)", () => {
  it("shows the original sentence and its actually-masked counterpart, computed by the real masking function", () => {
    render(<MaskPreview />);

    const preview = screen.getByLabelText("실제 마스킹 결과 미리보기");
    const [originalText, maskedText] = Array.from(preview.querySelectorAll("p")).map(
      (p) => p.textContent,
    );

    expect(originalText).toContain("홍길동님");
    expect(originalText).toContain("010-1234-5678");
    expect(originalText).toContain("hong@example.com");

    // applyMasking이 실제로 적용된 결과라면, 이름·전화번호·이메일 자리가 전부
    // 원래 글자 수만큼의 별표로 바뀌고 원문 값은 하나도 남지 않아야 한다.
    expect(maskedText).not.toContain("홍길동");
    expect(maskedText).not.toContain("010-1234-5678");
    expect(maskedText).not.toContain("hong@example.com");
    expect(maskedText).toContain("*".repeat(13)); // 010-1234-5678 (13자)
  });
});
