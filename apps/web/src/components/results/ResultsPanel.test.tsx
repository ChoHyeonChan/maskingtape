import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResultsPanel } from "./ResultsPanel";
import type { Detection } from "../../types/detection";

const name: Detection = { kind: "name", start: 0, end: 3, confidence: 0.9, detector: "T" };
const phone: Detection = { kind: "phone", start: 4, end: 17, confidence: 0.4, detector: "T" };
const scanned = { text: "김철수 010-1234-5678", detections: [name, phone] };

describe("ResultsPanel masking strength slider (#237, direction inverted by #264)", () => {
  it("does not render a slider before anything has been scanned", () => {
    render(<ResultsPanel scanned={null} activeFilter={null} scanRun={0} onFilterSelect={() => {}} />);
    expect(screen.queryByLabelText(/마스킹 강도/)).not.toBeInTheDocument();
  });

  it("defaults to 100% (rightmost = strongest) so every detection stays masked, matching prior behavior", () => {
    render(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />);
    expect(screen.getByLabelText(/마스킹 강도/)).toHaveValue("100");
    expect(screen.queryByText(/원문 그대로 표시됩니다/)).not.toBeInTheDocument();
    expect(screen.getByTestId("masked-result")).toHaveTextContent(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });

  it("lowering the strength (moving left) exposes low-confidence detections and warns how many", () => {
    render(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />);

    // 강도를 50으로 낮추면 확신도 50% 이상만 마스킹 대상이 된다
    fireEvent.change(screen.getByLabelText(/마스킹 강도/), { target: { value: "50" } });

    // phone(40%)만 제외되고 name(90%)은 그대로 마스킹된다
    expect(screen.getByText("1건은 마스킹되지 않고 원문 그대로 표시됩니다.", { exact: false })).toBeInTheDocument();
    expect(screen.getByTestId("masked-result")).toHaveTextContent(`${"*".repeat(3)} 010-1234-5678`);
  });

  it("automatically clears the filter once its target kind is hidden by the threshold, instead of leaving results stuck dimmed (#250)", () => {
    const onFilterSelect = vi.fn();
    render(<ResultsPanel scanned={scanned} activeFilter="phone" scanRun={1} onFilterSelect={onFilterSelect} />);

    // phone(40%)이 걸러지도록 임계값을 올린다 -- 필터 대상 카드 자체가 사라진다
    fireEvent.change(screen.getByLabelText(/마스킹 강도/), { target: { value: "50" } });

    expect(onFilterSelect).toHaveBeenCalledWith(null);
  });

  it("leaves the filter alone while its target kind is still visible", () => {
    const onFilterSelect = vi.fn();
    render(<ResultsPanel scanned={scanned} activeFilter="name" scanRun={1} onFilterSelect={onFilterSelect} />);

    fireEvent.change(screen.getByLabelText(/마스킹 강도/), { target: { value: "50" } });

    // name(90%)은 여전히 보이므로 필터를 건드리지 않는다
    expect(onFilterSelect).not.toHaveBeenCalled();
  });

  it("does not show the 'nothing found' reassurance when the threshold filters out every detection (#243)", () => {
    render(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />);

    // name(90%)·phone(40%) 둘 다 100% 미만이라 강도를 0(=확신도 임계값 100)으로 낮추면 전부 걸러진다
    fireEvent.change(screen.getByLabelText(/마스킹 강도/), { target: { value: "0" } });

    expect(screen.queryByText(/개인정보가 발견되지 않았습니다/)).not.toBeInTheDocument();
    expect(screen.getByText(/확신도 임계값보다 낮아 전부 가려져 있습니다/)).toBeInTheDocument();
    expect(screen.getByText("2건은 마스킹되지 않고 원문 그대로 표시됩니다.", { exact: false })).toBeInTheDocument();
  });

  it("resets the strength to 100 (mask everything) whenever a new scan (scanRun) comes in", () => {
    const { rerender } = render(
      <ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText(/마스킹 강도/), { target: { value: "50" } });
    expect(screen.getByLabelText(/마스킹 강도/)).toHaveValue("50");

    rerender(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={2} onFilterSelect={() => {}} />);

    expect(screen.getByLabelText(/마스킹 강도/)).toHaveValue("100");
  });
});
