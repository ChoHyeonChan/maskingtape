import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightedText } from "./HighlightedText";
import type { Detection } from "../types/detection";

function detection(overrides: Partial<Detection>): Detection {
  return {
    kind: "phone",
    start: 0,
    end: 0,
    text: "",
    confidence: 1,
    detector: "Test",
    ...overrides,
  };
}

describe("HighlightedText", () => {
  it("shows a placeholder message when there is no text yet", () => {
    render(<HighlightedText text="" detections={[]} />);
    expect(screen.getByText(/텍스트를 입력하고/)).toBeInTheDocument();
  });

  it("renders the detected span with its kind label and confidence in the tooltip", () => {
    const d = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });
    render(<HighlightedText text="연락처 010-1234-5678 입니다" detections={[d]} />);

    const mark = screen.getByText("010-1234-5678");
    expect(mark).toHaveClass("highlight--phone");
    expect(mark).toHaveAttribute("title", expect.stringContaining("전화번호"));
    expect(screen.getByText("전화번호", { selector: ".highlight__tag" })).toBeInTheDocument();
  });

  it("preserves the full original text across plain and highlighted segments", () => {
    const text = "이메일 test@example.com 로 문의";
    const d = detection({ kind: "email", start: 4, end: 20, text: "test@example.com" });
    render(<HighlightedText text={text} detections={[d]} />);
    expect(screen.getByTestId("highlighted-text")).toHaveTextContent("이메일 test@example.com이메일 로 문의");
  });

  it("marks low-confidence detections as uncertain but leaves confident ones plain", () => {
    const confident = detection({ kind: "phone", start: 0, end: 3, text: "확실함", confidence: 1 });
    render(<HighlightedText text="확실함" detections={[confident]} />);
    expect(screen.getByText("확실함")).not.toHaveClass("highlight--uncertain");

    const unsure = detection({ kind: "name", start: 0, end: 3, text: "김영희", confidence: 0.5 });
    render(<HighlightedText text="김영희" detections={[unsure]} />);
    expect(screen.getByText("김영희")).toHaveClass("highlight--uncertain");
  });
});
