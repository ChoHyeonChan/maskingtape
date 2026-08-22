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
        maskingStrength={100}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={0}
        onStrengthChange={() => {}}
        onToggle={() => {}}
        maskedText=""
      />,
    );
    expect(screen.getByText(/발견되지 않았습니다/)).toBeInTheDocument();
  });

  it("renders one row per detection with kind, snippet, and confidence, and a live count summary", () => {
    const rows = [
      row({ kind: "name", start: 0, end: 3, snippet: "김소연", confidence: 0.9, masked: true }),
      row({ kind: "phone", start: 4, end: 17, snippet: "010-1234-5678", confidence: 0.4, masked: false }),
    ];
    render(
      <DetectionList
        rows={rows}
        maskingStrength={65}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={50}
        onStrengthChange={() => {}}
        onToggle={() => {}}
        maskedText="김소연 010-1234-5678"
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
        maskingStrength={100}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={0}
        onStrengthChange={() => {}}
        onToggle={onToggle}
        maskedText="***"
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
        maskingStrength={0}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={100}
        onStrengthChange={() => {}}
        onToggle={() => {}}
        maskedText="김소연"
      />,
    );

    const toggle = screen.getByRole("switch", { name: /김소연/ });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toHaveTextContent("보임");
  });

  it("forwards the bulk confidence control's value and reacts to arrow clicks", () => {
    const onStrengthChange = vi.fn();
    render(
      <DetectionList
        rows={[row({ start: 0, end: 3 })]}
        maskingStrength={80}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={20}
        onStrengthChange={onStrengthChange}
        onToggle={() => {}}
        maskedText="***"
      />,
    );

    expect(screen.getByRole("spinbutton", { name: "마스킹 강도" })).toHaveAttribute("aria-valuenow", "80");
    fireEvent.click(screen.getByRole("button", { name: "마스킹 강도 올리기" }));
    expect(onStrengthChange).toHaveBeenCalledWith(85);
  });

  it("copies the given masked text (not something recomputed locally) when the copy button is clicked", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <DetectionList
        rows={[row({ start: 0, end: 3 })]}
        maskingStrength={100}
        minStrength={0}
        maxStrength={100}
        strengthStep={5}
        confidenceThreshold={0}
        onStrengthChange={() => {}}
        onToggle={() => {}}
        maskedText="완전한 마스킹 결과"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "마스킹 결과 복사" }));
    expect(writeText).toHaveBeenCalledWith("완전한 마스킹 결과");
  });
});
