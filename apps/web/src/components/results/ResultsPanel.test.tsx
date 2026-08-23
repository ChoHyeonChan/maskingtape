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

function rowFor(text: string) {
  const row = screen.getByRole("switch", { name: new RegExp(text) }).closest("li");
  if (!row) throw new Error(`row not found for ${text}`);
  return row;
}

describe("ResultsPanel confidence threshold control (#237, no longer inverted per user feedback)", () => {
  it("does not render the control before anything has been scanned", () => {
    render(<ResultsPanel scanned={null} scanRun={0} onMaskedTextChange={() => {}} />);
    expect(screen.queryByRole("spinbutton", { name: "확신도 임계값" })).not.toBeInTheDocument();
  });

  it("defaults to this scan's lowest confidence, so every detection starts out masked", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // phone(40%)이 이 스캔에서 가장 낮은 확신도라 임계값은 40에서 시작한다 -- 40 이상인
    // 둘 다(phone 40%, name 90%) 기본으로 가려진다.
    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "40");
    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });

  it("raising the threshold one step above the default excludes the weakest item first", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 기본값(40%)에서 한 단계만 올려도(45%) 가장 확신도 낮은 phone(40%)부터 바로 제외된다.
    setThresholdTo(45);
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

  it("resets the threshold to this scan's lowest confidence and clears per-item overrides whenever a new scan (scanRun) comes in", () => {
    const { rerender } = render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={() => {}} />);
    setThresholdTo(80);
    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "80");

    rerender(<ResultsPanel scanned={scanned} scanRun={2} onMaskedTextChange={() => {}} />);

    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "40");
  });
});

describe("ResultsPanel per-item toggle actually changes the masked result (not just a demo)", () => {
  it("reveals an above-threshold item when its toggle is switched off", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 기본값(이번 스캔 최저 확신도 40%)에서는 둘 다 가려져 있다 -- name만 수동으로 노출시킨다.
    toggleRow("김철수");

    expect(onMaskedTextChange).toHaveBeenLastCalledWith(`김철수 ${"*".repeat(13)}`);
  });

  it("forces a below-threshold item to stay masked when its toggle is switched on", () => {
    const onMaskedTextChange = vi.fn();
    render(<ResultsPanel scanned={scanned} scanRun={1} onMaskedTextChange={onMaskedTextChange} />);

    // 임계값을 올려 phone(40%)이 기본으로 노출되게 한 뒤, 수동으로 다시 가린다.
    setThresholdTo(45);
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

describe("ResultsPanel reports a highlight range for the left panel on row hover", () => {
  it("reports the item's own range and kind color on hover, and clears it on mouse leave", () => {
    const onHighlightChange = vi.fn();
    render(
      <ResultsPanel
        scanned={scanned}
        scanRun={1}
        onMaskedTextChange={() => {}}
        onHighlightChange={onHighlightChange}
      />,
    );

    // 기본값(40%)에서는 phone(40%)도 masked라 별표로 치환된 자리(4~17)를 가리켜야 한다.
    fireEvent.mouseEnter(rowFor("010-1234-5678"));
    expect(onHighlightChange).toHaveBeenLastCalledWith({ start: 4, end: 17, color: expect.any(String) });

    fireEvent.mouseLeave(rowFor("010-1234-5678"));
    expect(onHighlightChange).toHaveBeenLastCalledWith(null);
  });

  it("clears the highlight when a new scan comes in", () => {
    const onHighlightChange = vi.fn();
    const { rerender } = render(
      <ResultsPanel
        scanned={scanned}
        scanRun={1}
        onMaskedTextChange={() => {}}
        onHighlightChange={onHighlightChange}
      />,
    );

    fireEvent.mouseEnter(rowFor("김철수"));
    onHighlightChange.mockClear();

    rerender(
      <ResultsPanel
        scanned={scanned}
        scanRun={2}
        onMaskedTextChange={() => {}}
        onHighlightChange={onHighlightChange}
      />,
    );

    expect(onHighlightChange).toHaveBeenCalledWith(null);
  });
});
