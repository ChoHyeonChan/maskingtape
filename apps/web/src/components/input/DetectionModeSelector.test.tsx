// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DetectionModeSelector } from "./DetectionModeSelector";

describe("DetectionModeSelector (#547)", () => {
  it("shows rule-only as the selected mode and no OpenAI notice by default", () => {
    render(<DetectionModeSelector mode="rule" textLength={10} onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "규칙 전용" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "하이브리드 (OpenAI)" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("asks to switch to hybrid when the hybrid button is clicked", () => {
    const onChange = vi.fn();
    render(<DetectionModeSelector mode="rule" textLength={10} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));

    expect(onChange).toHaveBeenCalledWith("hybrid");
  });

  it("warns that masked text goes to OpenAI and that missed personal data can go with it, when hybrid is selected", () => {
    render(<DetectionModeSelector mode="hybrid" textLength={10} onChange={vi.fn()} />);

    const notice = screen.getByRole("note");
    expect(notice).toHaveTextContent("규칙으로 먼저 가린 글을 OpenAI로 보내");
    expect(notice).toHaveTextContent("규칙이 놓친 개인정보는 가린 글에 그대로 남아 함께 전송될 수 있으니");
    expect(notice).toHaveTextContent("실제 개인정보는 넣지 마세요");
  });

  it("disables hybrid and explains why when the text is over the hybrid limit, even if hybrid was selected", () => {
    render(<DetectionModeSelector mode="hybrid" textLength={5_001} onChange={vi.fn()} />);

    const hybrid = screen.getByRole("button", { name: "하이브리드 (OpenAI)" });
    expect(hybrid).toBeDisabled();
    expect(hybrid).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "규칙 전용" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("status")).toHaveTextContent("5,000자까지만 쓸 수 있어 규칙 전용으로 탐지합니다");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("allows hybrid at exactly the limit", () => {
    render(<DetectionModeSelector mode="hybrid" textLength={5_000} onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "하이브리드 (OpenAI)" })).toBeEnabled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("disables both buttons while disabled (e.g. during a re-scan)", () => {
    render(<DetectionModeSelector mode="rule" textLength={10} onChange={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "규칙 전용" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "하이브리드 (OpenAI)" })).toBeDisabled();
  });
});
