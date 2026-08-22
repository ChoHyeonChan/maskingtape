import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResultsPanel } from "./ResultsPanel";
import type { Detection } from "../../types/detection";

const name: Detection = { kind: "name", start: 0, end: 3, confidence: 0.9, detector: "T" };
const phone: Detection = { kind: "phone", start: 4, end: 17, confidence: 0.4, detector: "T" };
const scanned = { text: "김철수 010-1234-5678", detections: [name, phone] };

const STEP = 5;

/**
 * 확신도 임계값을 목표값까지 화살표 버튼으로 옮긴다. 컨트롤에 보이는 숫자가 곧 임계값이고
 * (더 이상 반전 없음), 이 값 이상인 항목만 기본으로 가려진다. 현재 값을 매번 다시 읽어서
 * 같은 테스트 안에서 여러 번 불러도 올바른 방향·횟수로 이동한다.
 */
function setThresholdTo(target: number) {
  const current = Number(screen.getByRole("spinbutton", { name: "확신도 임계값" }).getAttribute("aria-valuenow"));
  const diff = target - current;
  if (diff === 0) return;
  const button = screen.getByRole("button", { name: diff > 0 ? "확신도 임계값 올리기" : "확신도 임계값 내리기" });
  const clicks = Math.abs(diff) / STEP;
  for (let i = 0; i < clicks; i += 1) {
    fireEvent.click(button);
  }
}

function toggleRow(text: string) {
  fireEvent.click(screen.getByRole("switch", { name: new RegExp(text) }));
}

describe("ResultsPanel confidence threshold control (#237, no longer inverted per user feedback)", () => {
  it("does not render the control before anything has been scanned", () => {
    render(<ResultsPanel scanned={null} scanRun={0} onMaskedTextChange={() => {}} />);
    expect(screen.queryByRole("spinbutton", { name: "확신도 임계값" })).not.toBeInTheDocument();
  });

  it("defaults to 50%, masking mid/high-confidence detections but leaving lower-confidence ones exposed", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);
    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "50");

    // name(90%) >= 50 이라 가려지고, phone(40%) < 50 이라 그대로 노출된다.
    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} 010-1234-5678`);
  });

  it("raising the threshold above an item's own confidence excludes it, even if it was masked before", () => {
    const midConfidence: Detection = { kind: "name", start: 0, end: 3, confidence: 0.75, detector: "T" };
    const onMaskedTextChange = vi.fn();
    render(
      <ResultsPanel
        scanned={{ text: "김철수 010-1234-5678", detections: [midConfidence] }}
        scanRun={1}
        onMaskedTextChange={onMaskedTextChange}
      />,
    );

    // 임계값 80%에서는 75% 확신도인 항목이 기본으로 가려지지 않는다.
    setThresholdTo(80);
    expect(onMaskedTextChange).toHaveBeenLastCalledWith("김철수 010-1234-5678");

    // 정확히 75%로 낮추면(경계값, 이상 포함) 다시 가려진다.
    setThresholdTo(75);
    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} 010-1234-5678`);
  });

  it("lowering the threshold masks lower-confidence items too", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 임계값을 0으로 낮추면 phone(40%)도 가려진다.
    setThresholdTo(0);
    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });

  it("resets the threshold to 50% and clears per-item overrides whenever a new scan (scanRun) comes in", () => {
    const { rerender } = render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={() => {}} />);
    setThresholdTo(0);
    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "0");

    rerender(<ResultsPanel scanned={scanned} scanRun={2} onMaskedTextChange={() => {}} />);

    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "50");
  });
});

describe("ResultsPanel per-item toggle actually changes the masked result (not just a demo)", () => {
  it("reveals an above-threshold item when its toggle is switched off", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 기본값(50%)에서 name(90%)은 가려져 있다 -- 수동으로 노출시킨다.
    toggleRow("김철수");

    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`김철수 010-1234-5678`);
  });

  it("forces a below-threshold item to stay masked when its toggle is switched on", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // phone(40%)은 기본값(50%)에서 이미 노출 상태 -- 수동으로 가린다.
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
