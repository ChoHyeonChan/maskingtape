// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PRESETS } from "../../lib/presets";
import { ExampleGallery } from "./ExampleGallery";

describe("ExampleGallery (#455)", () => {
  it("shows every preset as its own card, not hidden behind a dropdown", () => {
    render(<ExampleGallery onPick={() => {}} />);

    for (const preset of PRESETS) {
      expect(screen.getByRole("button", { name: new RegExp(preset.label) })).toBeInTheDocument();
    }
  });

  it("shows a kind tag for each personal-info type the example actually contains", () => {
    render(<ExampleGallery onPick={() => {}} />);

    const contractCard = screen.getByRole("button", { name: /근로계약서 발췌/ });
    expect(contractCard).toHaveTextContent("이름");
    expect(contractCard).toHaveTextContent("주민등록번호");
    expect(contractCard).toHaveTextContent("주소");
    expect(contractCard).toHaveTextContent("전화번호");
  });

  it("passes the exact preset text to onPick when a card is clicked", () => {
    const onPick = vi.fn();
    render(<ExampleGallery onPick={onPick} />);

    fireEvent.click(screen.getByRole("button", { name: /여권번호/ }));

    const passportPreset = PRESETS.find((preset) => preset.label === "항공권 예약 확인서");
    expect(onPick).toHaveBeenCalledWith(passportPreset?.text);
  });
});
