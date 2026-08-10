import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { InputPanel } from "./InputPanel";

const MAX_TEXT_LENGTH = 100_000;

function renderPanel(text: string) {
  return render(
    <InputPanel
      text={text}
      hasResult={false}
      resultVersion={0}
      onTextChange={vi.fn()}
      onClear={vi.fn()}
      onResult={vi.fn()}
    />,
  );
}

describe("InputPanel input length safety (#154)", () => {
  it("does not show an over-limit warning under the max length", () => {
    renderPanel("안전한 길이의 입력입니다.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("reinforces the counter and announces an alert once pasted text exceeds the max length", () => {
    const overLength = "a".repeat(MAX_TEXT_LENGTH + 1);
    renderPanel(overLength);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("1자를 줄여주세요");

    const count = screen.getByText(`${overLength.length.toLocaleString()} / ${MAX_TEXT_LENGTH.toLocaleString()}자`);
    expect(count).toHaveClass("input-panel__count--over");
  });
});

describe("InputPanel contract demo preset (#215)", () => {
  it("loads the contract example text in one click, without opening the presets dropdown", () => {
    const onTextChange = vi.fn();
    render(
      <InputPanel
        text=""
        hasResult={false}
        resultVersion={0}
        onTextChange={onTextChange}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "계약서 예제" }));

    expect(onTextChange).toHaveBeenCalledWith(expect.stringContaining("근로계약서"));
  });
});
