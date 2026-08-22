import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResultsPanel } from "./ResultsPanel";
import type { Detection } from "../../types/detection";

const name: Detection = { kind: "name", start: 0, end: 3, confidence: 0.9, detector: "T" };
const phone: Detection = { kind: "phone", start: 4, end: 17, confidence: 0.4, detector: "T" };
const scanned = { text: "김철수 010-1234-5678", detections: [name, phone] };

const STEP = 5;

/** 마스킹 강도를 목표값까지 화살표 버튼으로 내린다(위/아래 화살표 컨트롤, #237/#264 계승). */
function lowerStrengthTo(target: number) {
  const decrease = screen.getByRole("button", { name: "마스킹 강도 내리기" });
  const clicks = (100 - target) / STEP;
  for (let i = 0; i < clicks; i += 1) {
    fireEvent.click(decrease);
  }
}

function toggleRow(text: string) {
  fireEvent.click(screen.getByRole("switch", { name: new RegExp(text) }));
}

describe("ResultsPanel masking strength control (#237, direction inverted by #264)", () => {
  it("does not render the control before anything has been scanned", () => {
    render(<ResultsPanel scanned={null} scanRun={0} onMaskedTextChange={() => {}} />);
    expect(screen.queryByRole("spinbutton", { name: "마스킹 강도" })).not.toBeInTheDocument();
  });

  it("defaults to 100% (strongest) so every detection stays masked, matching prior behavior", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);
    expect(screen.getByRole("spinbutton", { name: "마스킹 강도" })).toHaveAttribute("aria-valuenow", "100");
    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });

  it("lowering the strength auto-exposes low-confidence detections", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 강도를 50으로 낮추면 확신도 50% 이상만 기본으로 가려진다 -- phone(40%)만 제외
    lowerStrengthTo(50);

    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} 010-1234-5678`);
  });

  it("resets the strength and any per-item overrides whenever a new scan (scanRun) comes in", () => {
    const { rerender } = render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={() => {}} />);
    lowerStrengthTo(50);
    expect(screen.getByRole("spinbutton", { name: "마스킹 강도" })).toHaveAttribute("aria-valuenow", "50");

    rerender(<ResultsPanel scanned={scanned} scanRun={2} onMaskedTextChange={() => {}} />);

    expect(screen.getByRole("spinbutton", { name: "마스킹 강도" })).toHaveAttribute("aria-valuenow", "100");
  });
});

describe("ResultsPanel per-item toggle actually changes the masked result (not just a demo)", () => {
  it("reveals an above-threshold item when its toggle is switched off", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 강도 100%라 둘 다 기본으로 가려짐 -- name만 수동으로 노출
    toggleRow("김철수");

    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`김철수 ${"*".repeat(13)}`);
  });

  it("forces a below-threshold item to stay masked when its toggle is switched on", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // phone(40%)이 자동 노출되도록 강도를 낮춘 뒤, 수동으로 다시 가린다
    lowerStrengthTo(50);
    toggleRow("010-1234-5678");

    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });
});

describe("ResultsPanel scrolls to and focuses the results on scan completion (#308)", () => {
  it("does not scroll or focus before anything has been scanned", () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(<ResultsPanel scanned={null} scanRun={0} onMaskedTextChange={() => {}} />);

    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("scrolls the results into view and moves focus there once a scan completes", () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={() => {}} />);

    expect(scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ block: "start" }));
    expect(screen.getByRole("region", { name: "탐지 결과 조정" })).toHaveFocus();
  });

  it("scrolls and focuses again on every later scan, not just the first", () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    const { rerender } = render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={() => {}} />);
    expect(scrollIntoView).toHaveBeenCalledTimes(1);

    rerender(<ResultsPanel scanned={scanned} scanRun={2} onMaskedTextChange={() => {}} />);
    expect(scrollIntoView).toHaveBeenCalledTimes(2);
  });
});
