import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { scanText } from "./api/scanClient";

vi.mock("./api/scanClient", () => ({
  scanText: vi.fn(),
}));

const mockScanText = vi.mocked(scanText);

// mockScanText는 파일 전체에서 같은 인스턴스를 공유한다 — 매 테스트 전에 호출 이력을
// 지우지 않으면, 어떤 테스트가 먼저 스캔을 몇 번 했는지에 따라 뒤에 오는 다른 테스트의
// "toHaveBeenCalledTimes(N)" 같은 절대 횟수 검증이 테스트 실행 순서에 우연히 좌우된다.
beforeEach(() => {
  mockScanText.mockClear();
});

describe("App privacy banner (#154)", () => {
  it("always shows a privacy note warning against real personal data and recommending local install", () => {
    render(<App />);

    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    expect(note).toHaveTextContent("실제 개인정보는 입력하지 마세요");
    expect(note).toHaveTextContent("로컬 설치");
  });

  it("bolds the local-install recommendation, not the personal-data warning", () => {
    render(<App />);

    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    const strong = note.querySelector("strong");
    expect(strong).toHaveTextContent("정확한 결과가 필요하면 로컬 설치를 권장합니다");
    expect(strong).not.toHaveTextContent("개인정보");
  });
});

describe("App accuracy notice (#236)", () => {
  it("tells users the deployed demo is rule-only and links to local install for LLM accuracy", () => {
    render(<App />);

    const note = screen.getByRole("note", { name: "이름 탐지 정확도 안내" });
    expect(note).toHaveTextContent("규칙 기반 탐지만");
    expect(note).toHaveTextContent("로컬 LLM으로 이름까지 더 정확하게");

    const link = screen.getByRole("link", { name: "로컬 설치" });
    expect(link).toHaveAttribute("href", "https://github.com/ChoHyeonChan/maskingtape");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});

describe("App lets you click the masked-result box to edit and re-scan", () => {
  it("returns to the editable original text (not the masked text) when the result box is clicked, and can be re-scanned", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "phone", start: 4, end: 17, confidence: 1, detector: "test" }],
    });
    render(<App />);

    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: "연락처 010-1234-5678" } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));

    const resultBox = await screen.findByRole("textbox", { name: "마스킹된 탐지 결과" });
    await waitFor(() => expect(resultBox).toHaveValue("연락처 *************"));

    fireEvent.click(resultBox);

    // 클릭 한 번으로 "문서 입력" 상태로 돌아가되, 마스킹된 텍스트가 아니라 원래
    // 입력했던 원문이 그대로(수정 가능하게) 남아 있어야 한다.
    const editableBox = screen.getByRole("textbox", { name: "탐지할 텍스트 입력" });
    expect(editableBox).toHaveValue("연락처 010-1234-5678");
    expect(editableBox).not.toHaveAttribute("readonly");

    // 이어서 수정하고 다시 탐지할 수 있다.
    fireEvent.change(editableBox, { target: { value: "연락처 010-9999-0000" } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith("연락처 010-9999-0000"));
  });
});

describe("App result coachmark (#299)", () => {
  it("shows the intro coachmark on first load", () => {
    render(<App />);

    const dialog = screen.getByRole("dialog", { name: "사용 방법 안내" });
    expect(dialog).toHaveTextContent("처음이라면");
  });

  it("auto-opens the result coachmark once right after the first scan, and does not reopen it on a later scan", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "name", start: 0, end: 2, confidence: 1, detector: "test" }],
    });
    render(<App />);

    // 인트로 코치마크가 스캔 버튼을 덮고 있으므로 먼저 닫는다 (실제 사용자 흐름과 동일).
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: "김철수 010-1234-5678" } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));

    await waitFor(() =>
      expect(screen.getByRole("dialog", { name: "사용 방법 안내" })).toHaveTextContent("완료!"),
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "초기화 하기" }));
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: "다른 문장 010-9999-8888" } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));

    await waitFor(() => expect(mockScanText).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the result coachmark (not the intro one) from the help button while a result is showing", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "name", start: 0, end: 2, confidence: 1, detector: "test" }],
    });
    render(<App />);

    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: "김철수 010-1234-5678" } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));
    await waitFor(() => screen.getByRole("dialog"));

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "사용 안내 다시 보기" }));

    expect(screen.getByRole("dialog", { name: "사용 방법 안내" })).toHaveTextContent("완료!");
  });
});
