import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetectionSummary } from "./DetectionSummary";
import type { Detection } from "../../types/detection";

function d(kind: string, confidence = 1): Detection {
  return { kind, start: 0, end: 0, confidence, detector: "T" };
}

describe("DetectionSummary", () => {
  it("shows a reassuring message when nothing was detected", () => {
    render(<DetectionSummary detections={[]} activeFilter={null} onFilterSelect={() => {}} />);
    expect(screen.getByText(/발견되지 않았습니다/)).toBeInTheDocument();
  });

  it("shows the total count and per-kind breakdown with Korean labels", () => {
    render(<DetectionSummary detections={[d("phone"), d("phone"), d("rrn")]} activeFilter={null} onFilterSelect={() => {}} />);
    expect(screen.getByText(/개인정보 3건 발견/)).toBeInTheDocument();
    expect(screen.getByText(/전화번호 2/)).toBeInTheDocument();
    expect(screen.getByText(/주민등록번호 1/)).toBeInTheDocument();
  });

  it("falls back to the raw kind string for a kind with no Korean label mapping, without crashing (#216)", () => {
    render(<DetectionSummary detections={[d("account")]} activeFilter={null} onFilterSelect={() => {}} />);
    expect(screen.getByText(/개인정보 1건 발견/)).toBeInTheDocument();
    expect(screen.getByText(/account 1/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "account 보기" })).toHaveClass("summary__filter--account");
  });

  it("renders a confidence bar sized to the lowest confidence within a kind, not the average (#237)", () => {
    const { container } = render(
      <DetectionSummary
        detections={[d("name", 0.9), d("name", 0.5)]}
        activeFilter={null}
        onFilterSelect={() => {}}
      />,
    );

    expect(screen.getByText(/이름 2건, 최소 확신도 50%/)).toBeInTheDocument();
    const barFill = container.querySelector(".summary-card--name .summary-card__bar-fill") as HTMLElement;
    expect(barFill.style.width).toBe("50%");
  });
});
