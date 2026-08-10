import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultsPanel } from "./ResultsPanel";
import type { Detection } from "../../types/detection";

const name: Detection = { kind: "name", start: 0, end: 3, confidence: 0.9, detector: "T" };
const phone: Detection = { kind: "phone", start: 4, end: 17, confidence: 0.4, detector: "T" };
const scanned = { text: "김철수 010-1234-5678", detections: [name, phone] };

describe("ResultsPanel confidence threshold slider (#237)", () => {
  it("does not render a slider before anything has been scanned", () => {
    render(<ResultsPanel scanned={null} activeFilter={null} scanRun={0} onFilterSelect={() => {}} />);
    expect(screen.queryByLabelText(/확신도/)).not.toBeInTheDocument();
  });

  it("defaults to 0% so every detection stays masked, matching prior behavior", () => {
    render(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />);
    expect(screen.getByLabelText(/확신도/)).toHaveValue("0");
    expect(screen.queryByText(/원문 그대로 표시됩니다/)).not.toBeInTheDocument();
    expect(screen.getByTestId("masked-result")).toHaveTextContent(`${"*".repeat(3)} ${"*".repeat(13)}`);
  });

  it("excludes detections below the chosen threshold from masking and warns how many", () => {
    render(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />);

    fireEvent.change(screen.getByLabelText(/확신도/), { target: { value: "50" } });

    // phone(40%)만 제외되고 name(90%)은 그대로 마스킹된다
    expect(screen.getByText("1건은 마스킹되지 않고 원문 그대로 표시됩니다.", { exact: false })).toBeInTheDocument();
    expect(screen.getByTestId("masked-result")).toHaveTextContent(`${"*".repeat(3)} 010-1234-5678`);
  });

  it("resets the threshold to 0 whenever a new scan (scanRun) comes in", () => {
    const { rerender } = render(
      <ResultsPanel scanned={scanned} activeFilter={null} scanRun={1} onFilterSelect={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText(/확신도/), { target: { value: "50" } });
    expect(screen.getByLabelText(/확신도/)).toHaveValue("50");

    rerender(<ResultsPanel scanned={scanned} activeFilter={null} scanRun={2} onFilterSelect={() => {}} />);

    expect(screen.getByLabelText(/확신도/)).toHaveValue("0");
  });
});
