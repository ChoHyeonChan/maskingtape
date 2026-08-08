import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HighlightedText } from "./HighlightedText";
import type { Detection } from "../../types/detection";

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
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a placeholder message when there is no text yet", () => {
    render(<HighlightedText text="" detections={[]} activeFilter={null} />);
    expect(screen.getByText(/텍스트를 입력하고/)).toBeInTheDocument();
  });

  it("renders the detected span with its kind label and confidence in the tooltip", () => {
    const d = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });
    render(<HighlightedText text="연락처 010-1234-5678 입니다" detections={[d]} activeFilter={null} />);

    const mark = screen.getByText("010-1234-5678");
    expect(mark).toHaveClass("highlight--phone");
    expect(mark).not.toHaveClass("highlight--covered");
    expect(mark).toHaveAttribute("title", expect.stringContaining("전화번호"));
    expect(screen.getByText("전화번호", { selector: ".highlight__tag" })).toBeInTheDocument();
  });

  it("exposes kind and confidence via aria-label so keyboard/screen-reader users don't need the hover tooltip (#106)", () => {
    const confident = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });
    render(<HighlightedText text="연락처 010-1234-5678 입니다" detections={[confident]} activeFilter={null} />);
    expect(screen.getByRole("button", { name: "전화번호 · 신뢰도 100% · 가리기" })).toBeInTheDocument();
  });

  it("shows the exact confidence percentage on the visible tag for uncertain detections (#106)", () => {
    const unsure = detection({ kind: "name", start: 0, end: 3, text: "김영희", confidence: 0.5 });
    render(<HighlightedText text="김영희" detections={[unsure]} activeFilter={null} />);
    expect(screen.getByText("이름 · 50%", { selector: ".highlight__tag" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이름 · 신뢰도 50% · 가리기" })).toBeInTheDocument();
  });

  it("renders core business registration detections with the business color class", () => {
    const d = detection({ kind: "biz_reg", start: 3, end: 15, text: "123-45-67890", confidence: 1 });
    render(<HighlightedText text="번호 123-45-67890 확인" detections={[d]} activeFilter={null} />);

    const mark = screen.getByText("123-45-67890");
    expect(mark).toHaveClass("highlight--biz_reg");
    expect(screen.getByText("사업자등록번호", { selector: ".highlight__tag" })).toBeInTheDocument();
  });

  it("preserves the full original text across plain and highlighted segments", () => {
    const text = "이메일 test@example.com 로 문의";
    const d = detection({ kind: "email", start: 4, end: 20, text: "test@example.com" });
    render(<HighlightedText text={text} detections={[d]} activeFilter={null} />);
    expect(screen.getByTestId("highlighted-text")).toHaveTextContent("이메일 test@example.com이메일 로 문의");
  });

  it("marks low-confidence detections as uncertain but leaves confident ones plain", () => {
    const confident = detection({ kind: "phone", start: 0, end: 3, text: "확실함", confidence: 1 });
    render(<HighlightedText text="확실함" detections={[confident]} activeFilter={null} />);
    expect(screen.getByText("확실함")).not.toHaveClass("highlight--uncertain");

    const unsure = detection({ kind: "name", start: 0, end: 3, text: "김영희", confidence: 0.5 });
    render(<HighlightedText text="김영희" detections={[unsure]} activeFilter={null} />);
    expect(screen.getByText("김영희")).toHaveClass("highlight--uncertain");
  });

  it("covers a detected item when it is clicked", () => {
    const d = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });
    render(<HighlightedText text="연락처 010-1234-5678 입니다" detections={[d]} activeFilter={null} />);

    const mark = screen.getByRole("button", { name: "전화번호 · 신뢰도 100% · 가리기" });
    fireEvent.click(mark);

    expect(mark).toHaveClass("highlight--covered");
    expect(mark).toHaveAttribute("aria-pressed", "true");
  });

  it("toggles every detected item from the cover-all button", () => {
    const phone = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });
    const email = detection({ kind: "email", start: 20, end: 36, text: "hong@example.com", confidence: 1 });

    render(
      <HighlightedText
        text="문의 010-1234-5678 / hong@example.com"
        detections={[phone, email]}
        activeFilter={null}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "모두 가리기" }));

    expect(screen.getByRole("button", { name: "전화번호 · 신뢰도 100% · 가림 해제" })).toHaveClass("highlight--covered");
    expect(screen.getByRole("button", { name: "이메일 · 신뢰도 100% · 가림 해제" })).toHaveClass("highlight--covered");

    fireEvent.click(screen.getByRole("button", { name: "가리기 전으로" }));

    expect(screen.getByRole("button", { name: "전화번호 · 신뢰도 100% · 가리기" })).not.toHaveClass("highlight--covered");
    expect(screen.getByRole("button", { name: "이메일 · 신뢰도 100% · 가리기" })).not.toHaveClass("highlight--covered");
  });

  it("briefly reveals covered items when their filter is selected", () => {
    vi.useFakeTimers();
    const phone = detection({ kind: "phone", start: 4, end: 17, text: "010-1234-5678", confidence: 1 });

    const { rerender } = render(
      <HighlightedText text="문의 010-1234-5678" detections={[phone]} activeFilter={null} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "모두 가리기" }));
    const mark = screen.getByRole("button", { name: "전화번호 · 신뢰도 100% · 가림 해제" });
    expect(mark).toHaveClass("highlight--covered");

    rerender(<HighlightedText text="문의 010-1234-5678" detections={[phone]} activeFilter="phone" />);
    expect(mark).toHaveClass("highlight--revealed");

    act(() => {
      vi.advanceTimersByTime(6500);
    });
    expect(mark).toHaveClass("highlight--covered");
  });

  it("shows an additional masked result below the interactive result", () => {
    const phone = detection({ kind: "phone", start: 3, end: 16, text: "010-1234-5678", confidence: 1 });
    const email = detection({ kind: "email", start: 19, end: 35, text: "hong@example.com", confidence: 1 });

    render(
      <HighlightedText
        text="문의 010-1234-5678 / hong@example.com"
        detections={[phone, email]}
        activeFilter={null}
      />,
    );

    expect(screen.getByTestId("highlighted-text")).toHaveTextContent("010-1234-5678");
    expect(screen.getByTestId("masked-result")).toHaveTextContent("문의 ************* / ****************");
    expect(screen.getByTestId("masked-result")).not.toHaveTextContent("010-1234-5678");
    expect(screen.getByTestId("masked-result")).not.toHaveTextContent("hong@example.com");
  });
});
