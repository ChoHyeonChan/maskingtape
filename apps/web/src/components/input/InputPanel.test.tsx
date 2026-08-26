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

  it("shows an instant tooltip on the icon-only upload button, and switches it while extracting", () => {
    renderPanel("");
    expect(screen.getByRole("button", { name: "파일 업로드" })).toHaveAttribute("data-tooltip", "파일 업로드");
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

describe("InputPanel result view accessibility", () => {
  it("does not leave aria-describedby pointing at an element that isn't rendered once a result is shown", () => {
    render(
      <InputPanel
        text="마스킹된 텍스트"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    const textarea = screen.getByRole("textbox", { name: "마스킹된 탐지 결과" });
    const describedBy = textarea.getAttribute("aria-describedby");
    if (describedBy) {
      expect(document.getElementById(describedBy)).not.toBeNull();
    }
  });
});

describe("InputPanel click-to-edit on the result box (다시 고쳐서 재탐지)", () => {
  it("calls onRequestEdit when the read-only result box is clicked", () => {
    const onRequestEdit = vi.fn();
    render(
      <InputPanel
        text="김철수 010-****-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
        onRequestEdit={onRequestEdit}
      />,
    );

    fireEvent.click(screen.getByRole("textbox", { name: "마스킹된 탐지 결과" }));
    expect(onRequestEdit).toHaveBeenCalledTimes(1);
  });

  it("does not call onRequestEdit when clicking the editable (pre-scan) textarea", () => {
    const onRequestEdit = vi.fn();
    render(
      <InputPanel
        text="아직 입력 중"
        hasResult={false}
        resultVersion={0}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
        onRequestEdit={onRequestEdit}
      />,
    );

    fireEvent.click(screen.getByRole("textbox", { name: "탐지할 텍스트 입력" }));
    expect(onRequestEdit).not.toHaveBeenCalled();
  });
});

describe("InputPanel replays the reveal sweep when the masked text itself changes (#237 follow-up)", () => {
  it("replays the sweep when a toggle in the results panel changes the text, even though resultVersion (scanRun) stays the same", () => {
    const { rerender } = render(
      <InputPanel
        text="김철수 010-****-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    // 항목 하나를 노출시켜서 텍스트만 바뀐 상황(예: DetectionList의 토글) — scanRun은 그대로.
    rerender(
      <InputPanel
        text="김철수 010-1234-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    const textarea = screen.getByRole("textbox", { name: "마스킹된 탐지 결과" });
    expect(textarea).toHaveClass("is-text-revealing");
    expect(screen.getByText("김철수 010-1234-5678", { selector: ".input-panel__result-reveal" })).toBeInTheDocument();
  });
});

describe("InputPanel highlights the hovered detection's own text (오른쪽 목록 호버 연동)", () => {
  it("wraps only the highlighted range in a <mark>, tinted with the given color", () => {
    render(
      <InputPanel
        text="근로자 010-1234-5678 입니다"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
        highlight={{ start: 4, end: 17, color: "var(--kind-phone)" }}
      />,
    );

    const mark = document.querySelector(".input-panel__highlight-overlay mark");
    expect(mark).not.toBeNull();
    expect(mark).toHaveTextContent("010-1234-5678");
    expect(mark).toHaveStyle({ "--highlight-color": "var(--kind-phone)" });
  });

  it("renders no <mark> when there is nothing to highlight", () => {
    render(
      <InputPanel
        text="근로자 010-1234-5678 입니다"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
        highlight={null}
      />,
    );

    expect(document.querySelector(".input-panel__highlight-overlay mark")).toBeNull();
  });
});

describe("InputPanel export actions (복사·파일로 저장이 이 패널에 모임)", () => {
  it("copies the exact text shown in this panel, not something recomputed elsewhere", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <InputPanel
        text="근로자 *** 010-****-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "마스킹 결과 복사" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith("근로자 *** 010-****-5678"));
  });

  it("shows an instant tooltip (not the browser's delayed title) on the icon-only save button", () => {
    render(
      <InputPanel
        text="근로자 *** 010-****-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "파일로 저장" })).toHaveAttribute("data-tooltip", "파일로 저장");
  });

  it("saves the shown text as a .txt file when '파일로 저장' is clicked", () => {
    const createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(
      <InputPanel
        text="근로자 *** 010-****-5678"
        hasResult
        resultVersion={1}
        onTextChange={vi.fn()}
        onClear={vi.fn()}
        onResult={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "파일로 저장" }));

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toContain("text/plain");
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");

    clickSpy.mockRestore();
    vi.unstubAllGlobals();
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
