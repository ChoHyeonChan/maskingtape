import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

describe("InputPanel mask mode toggle (#277)", () => {
  it("does not show the toggle before there is a result", () => {
    renderPanel("아직 스캔 전");
    expect(screen.queryByRole("group", { name: "마스킹 방식 선택" })).not.toBeInTheDocument();
  });

  it("shows the toggle once a result exists and reports the chosen mode", () => {
    const onMaskModeChange = vi.fn();
    render(
      <InputPanel
        text="김철수 ***"
        hasResult
        resultVersion={1}
        maskMode="mask"
        onMaskModeChange={onMaskModeChange}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "별표" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "라벨" })).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(screen.getByRole("button", { name: "라벨" }));
    expect(onMaskModeChange).toHaveBeenCalledWith("label");
  });
});

describe("InputPanel file upload (#263)", () => {
  it("fills the textarea with a .txt file's content, never uploading the file itself to a server", async () => {
    const onTextChange = vi.fn();
    renderPanelWithChange(onTextChange);

    const file = new File(["고객 홍길동님 연락처 010-1234-5678"], "메모.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("txt 또는 텍스트 PDF 파일 업로드"), { target: { files: [file] } });

    await waitFor(() => expect(onTextChange).toHaveBeenCalledWith("고객 홍길동님 연락처 010-1234-5678"));
  });

  it("shows a clear error for an unsupported file type instead of silently failing", async () => {
    renderPanel("");

    const file = new File(["binary"], "photo.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("txt 또는 텍스트 PDF 파일 업로드"), { target: { files: [file] } });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("지원하지 않는 파일 형식입니다"),
    );
  });

  it("also accepts a file dropped onto the input area", async () => {
    const onTextChange = vi.fn();
    renderPanelWithChange(onTextChange);

    const file = new File(["드래그로 넣은 텍스트"], "드래그.txt", { type: "text/plain" });
    const dropZone = screen.getByLabelText("탐지할 텍스트 입력").closest(".input-panel__textarea-wrap");
    if (!dropZone) throw new Error("drop zone not found");

    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });

    await waitFor(() => expect(onTextChange).toHaveBeenCalledWith("드래그로 넣은 텍스트"));
  });
});

function renderPanelWithChange(onTextChange: (text: string) => void) {
  return render(
    <InputPanel
      text=""
      hasResult={false}
      resultVersion={0}
      onTextChange={onTextChange}
      onClear={vi.fn()}
      onResult={vi.fn()}
    />,
  );
}

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
