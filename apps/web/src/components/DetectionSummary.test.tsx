import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DetectionSummary } from "./DetectionSummary";
import type { Detection } from "../types/detection";

function d(kind: string): Detection {
  return { kind, start: 0, end: 0, text: "", confidence: 1, detector: "T" };
}

describe("DetectionSummary", () => {
  it("shows a reassuring message when nothing was detected", () => {
    render(<DetectionSummary detections={[]} />);
    expect(screen.getByText(/발견되지 않았습니다/)).toBeInTheDocument();
  });

  it("shows the total count and per-kind breakdown with Korean labels", () => {
    render(<DetectionSummary detections={[d("phone"), d("phone"), d("rrn")]} />);
    expect(screen.getByText(/개인정보 3건 발견/)).toBeInTheDocument();
    expect(screen.getByText(/전화번호 2/)).toBeInTheDocument();
    expect(screen.getByText(/주민등록번호 1/)).toBeInTheDocument();
  });
});
