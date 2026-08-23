import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DetectionList } from "./DetectionList";
import type { Detection } from "../../types/detection";

function detection(overrides: Partial<Detection>): Detection {
  return { kind: "phone", start: 0, end: 0, confidence: 1, detector: "T", ...overrides };
}

function row(overrides: Partial<Detection> & { snippet?: string; masked?: boolean }) {
  const { snippet = "", masked = true, ...rest } = overrides;
  const d = detection(rest);
  return { detection: d, key: `${d.kind}:${d.start}:${d.end}`, snippet, masked };
}

describe("DetectionList", () => {
  it("shows a reassuring message when nothing was detected", () => {
    render(
      <DetectionList
        rows={[]}
        confidenceThreshold={50}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );
    expect(screen.getByText(/발견되지 않았습니다/)).toBeInTheDocument();
  });

  it("does not show a confidence-threshold percentage next to the bulk control's own value — showing two different-looking numbers together was confusing", () => {
    render(
      <DetectionList
        rows={[row({ start: 0, end: 3 })]}
        confidenceThreshold={60}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );

    expect(screen.queryByText(/이상은 기본으로 가립니다/)).not.toBeInTheDocument();
    expect(screen.getByText(/확신도가 이 값 이상인 항목만 기본으로 가려집니다/)).toBeInTheDocument();
  });

  it("renders one row per detection with kind, snippet, and confidence, and a live count summary", () => {
    const rows = [
      row({ kind: "name", start: 0, end: 3, snippet: "김소연", confidence: 0.9, masked: true }),
      row({ kind: "phone", start: 4, end: 17, snippet: "010-1234-5678", confidence: 0.4, masked: false }),
    ];
    render(
      <DetectionList
        rows={rows}
        confidenceThreshold={65}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );

    expect(screen.getByText("김소연")).toBeInTheDocument();
    expect(screen.getByText("010-1234-5678")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText(/개인정보 2건 발견/)).toBeInTheDocument();
    expect(screen.getByText(/1건 가림/)).toBeInTheDocument();
    expect(screen.getByText(/1건 노출/)).toBeInTheDocument();
  });

  it("calls onToggle with the detection when its row switch is clicked", () => {
    const onToggle = vi.fn();
    const d = detection({ kind: "name", start: 0, end: 3 });
    render(
      <DetectionList
        rows={[{ detection: d, key: "name:0:3", snippet: "김소연", masked: true }]}
        confidenceThreshold={0}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={onToggle}
        onRowHover={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("switch", { name: /김소연/ }));
    expect(onToggle).toHaveBeenCalledWith(d);
  });

  it("reflects the masked state via the switch's aria-checked and label", () => {
    const d = detection({ kind: "name", start: 0, end: 3 });
    render(
      <DetectionList
        rows={[{ detection: d, key: "name:0:3", snippet: "김소연", masked: false }]}
        confidenceThreshold={100}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );

    const toggle = screen.getByRole("switch", { name: /김소연/ });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toHaveTextContent("보임");
  });

  it("forwards the bulk confidence control's value and reacts to arrow clicks", () => {
    const onThresholdChange = vi.fn();
    render(
      <DetectionList
        rows={[row({ start: 0, end: 3 })]}
        confidenceThreshold={80}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={onThresholdChange}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );

    expect(screen.getByRole("spinbutton", { name: "확신도 임계값" })).toHaveAttribute("aria-valuenow", "80");
    fireEvent.click(screen.getByRole("button", { name: "확신도 임계값 올리기" }));
    expect(onThresholdChange).toHaveBeenCalledWith(85);
  });

  it("does not render its own copy/download actions — those live in the masking-result panel instead", () => {
    render(
      <DetectionList
        rows={[row({ start: 0, end: 3 })]}
        confidenceThreshold={50}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={() => {}}
      />,
    );

    expect(screen.queryByRole("button", { name: "마스킹 결과 복사" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다운로드" })).not.toBeInTheDocument();
  });

  it("reports the hovered row's key on mouse enter and null on mouse leave", () => {
    const onRowHover = vi.fn();
    const d = detection({ kind: "name", start: 0, end: 3 });
    render(
      <DetectionList
        rows={[{ detection: d, key: "name:0:3", snippet: "김소연", masked: true }]}
        confidenceThreshold={50}
        minThreshold={0}
        maxThreshold={100}
        thresholdStep={5}
        onThresholdChange={() => {}}
        onToggle={() => {}}
        onRowHover={onRowHover}
      />,
    );

    const listItem = screen.getByRole("switch", { name: /김소연/ }).closest("li");
    if (!listItem) throw new Error("row not found");

    fireEvent.mouseEnter(listItem);
    expect(onRowHover).toHaveBeenLastCalledWith("name:0:3");

    fireEvent.mouseLeave(listItem);
    expect(onRowHover).toHaveBeenLastCalledWith(null);
  });
});
