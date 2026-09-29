// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PRESETS } from "../../lib/presets";
import { ResultsPanel } from "./ResultsPanel";
import { SampleTabs } from "./SampleTabs";

describe("SampleTabs (스캔 전 결과 자리를 샘플 서랍으로)", () => {
  it("shows every preset as a tab, with the first one selected", () => {
    render(<SampleTabs onPick={() => {}} />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(PRESETS.map((preset) => preset.label));
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent(PRESETS[0].text);
  });

  it("previews the clicked tab without touching the input until the use button is pressed", () => {
    const onPick = vi.fn();
    render(<SampleTabs onPick={onPick} />);

    fireEvent.click(screen.getByRole("tab", { name: "근로계약서 발췌" }));
    const contract = PRESETS.find((preset) => preset.label === "근로계약서 발췌")!;
    expect(screen.getByRole("tabpanel").textContent).toContain("김소연");
    expect(onPick).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "입력창에 넣기" }));
    expect(onPick).toHaveBeenCalledWith(contract.text);
  });

  it("moves between tabs with the arrow keys and wraps around", () => {
    render(<SampleTabs onPick={() => {}} />);
    const tabs = screen.getAllByRole("tab");

    fireEvent.keyDown(tabs[0], { key: "ArrowLeft" });
    expect(tabs[tabs.length - 1]).toHaveAttribute("aria-selected", "true");
    expect(tabs[tabs.length - 1]).toHaveFocus();

    fireEvent.keyDown(tabs[tabs.length - 1], { key: "ArrowRight" });
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
  });

  it("takes the results panel's place only before a scan", () => {
    const { rerender } = render(<ResultsPanel scanned={null} scanRun={0} onMaskedTextChange={() => {}} />);
    expect(screen.getByRole("tablist", { name: "샘플 문서" })).toBeInTheDocument();

    rerender(
      <ResultsPanel scanned={{ text: "샘플", detections: [] }} scanRun={1} onMaskedTextChange={() => {}} />,
    );
    expect(screen.queryByRole("tablist", { name: "샘플 문서" })).not.toBeInTheDocument();
  });
});
