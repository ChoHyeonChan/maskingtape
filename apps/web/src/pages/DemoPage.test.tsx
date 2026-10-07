// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DemoPage } from "./DemoPage";
import { scanText } from "../api/scanClient";

vi.mock("../api/scanClient", () => ({
  scanText: vi.fn(),
}));

const mockScanText = vi.mocked(scanText);

// mockScanText는 파일 전체에서 같은 인스턴스를 공유한다 — 매 테스트 전에 호출 이력을
// 지우지 않으면, 어떤 테스트가 먼저 스캔을 몇 번 했는지에 따라 뒤에 오는 다른 테스트의
// "toHaveBeenCalledTimes(N)" 같은 절대 횟수 검증이 테스트 실행 순서에 우연히 좌우된다.
beforeEach(() => {
  mockScanText.mockClear();
});

describe("DemoPage privacy banner (#154)", () => {
  it("always shows a privacy note warning against real personal data and recommending local install", () => {
    render(<DemoPage />);

    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    expect(note).toHaveTextContent("실제 개인정보는 입력하지 마세요");
    expect(note).toHaveTextContent("로컬 설치");
  });

  it("bolds the local-install recommendation, not the personal-data warning", () => {
    render(<DemoPage />);

    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    const strong = note.querySelector("strong");
    expect(strong).toHaveTextContent("정확한 결과가 필요하면 로컬 설치를 권장합니다");
    expect(strong).not.toHaveTextContent("개인정보");
  });

  it("discloses that input is sent to the server for analysis, not processed locally (#499)", () => {
    render(<DemoPage />);

    // d4f1bb5(2026-08-26)에서 "로컬에서만 처리" 문구가 빠졌는데, 배포판은 실제로
    // /api/scan 서버 호출을 거치므로 그 문구는 틀린 말이었다 — 실제 동작과 같은
    // "서버로 전송된다"는 안내가 있어야 한다. 저장하지 않는다는 약속은 우리 코드
    // 범위로만 좁힌다 — 배포 플랫폼(Vercel)의 요청 기록은 우리 코드 밖이다.
    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    expect(note).toHaveTextContent("서버로 전송되며, 우리 코드는 요청 내용을 저장하거나 기록하지 않습니다");
  });
});

describe("DemoPage lets you click the masked-result box to edit and re-scan", () => {
  it("returns to the editable original text (not the masked text) when the result box is clicked, and can be re-scanned", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "phone", start: 4, end: 17, confidence: 1, detector: "test" }],
    });
    render(<DemoPage />);

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

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith("연락처 010-9999-0000", "rule"));
  });
});

describe("DemoPage result coachmark (#299)", () => {
  it("shows the intro coachmark on first load", () => {
    render(<DemoPage />);

    const dialog = screen.getByRole("dialog", { name: "사용 방법 안내" });
    expect(dialog).toHaveTextContent("처음이라면");
  });

  it("auto-opens the result coachmark once right after the first scan, and does not reopen it on a later scan", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "name", start: 0, end: 2, confidence: 1, detector: "test" }],
    });
    render(<DemoPage />);

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
    render(<DemoPage />);

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

describe("DemoPage detection mode (#547)", () => {
  function scan(text: string) {
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: text } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));
  }

  it("scans rule-only by default", async () => {
    mockScanText.mockResolvedValue({ detections: [] });
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });

    scan("고객 김민준");

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith("고객 김민준", "rule"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("sends hybrid when chosen, and marks the names the OpenAI judge added", async () => {
    mockScanText.mockResolvedValue({
      detections: [
        { kind: "phone", start: 7, end: 20, confidence: 1, detector: "PhoneDetector" },
        { kind: "name", start: 3, end: 6, confidence: 0.9, detector: "OpenAINameJudge" },
      ],
      mode_used: "hybrid",
      hybrid_failed: false,
      hybrid_failure_code: null,
    });
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));
    scan("고객 김민준 010-1234-5678");

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith("고객 김민준 010-1234-5678", "hybrid"));
    expect(await screen.findByText(/규칙이 놓친 이름/)).toHaveTextContent("1건");
    expect(screen.getByRole("switch", { name: /이름\(LLM\) 김민준/ })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /^전화번호 010/ })).toBeInTheDocument();
  });

  it("tells the user when hybrid fell back to rule results instead of passing silently", async () => {
    mockScanText.mockResolvedValue({
      detections: [{ kind: "phone", start: 7, end: 20, confidence: 1, detector: "PhoneDetector" }],
      mode_used: "rule",
      hybrid_failed: true,
      hybrid_failure_code: "rate_limited",
    });
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));
    scan("고객 김민준 010-1234-5678");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("하이브리드 판단에 실패해 규칙 전용 결과만 보여 줍니다");
    expect(alert).toHaveTextContent("잠시 후 다시 시도해 주세요");
  });

  it("sends rule-only when the text is over the hybrid limit, even with hybrid chosen", async () => {
    mockScanText.mockResolvedValue({ detections: [] });
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));
    const longText = "가".repeat(5_001);
    scan(longText);

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith(longText, "rule"));
  });
});

describe("DemoPage switch detection mode from the result screen (#547 follow-up)", () => {
  const TEXT = "고객 김민준 010-1234-5678";
  const ruleResult = {
    detections: [{ kind: "phone", start: 7, end: 20, confidence: 1, detector: "PhoneDetector" }],
    mode_used: "rule" as const,
    hybrid_failed: false,
    hybrid_failure_code: null,
  };
  const hybridResult = {
    detections: [
      { kind: "name", start: 3, end: 6, confidence: 0.9, detector: "OpenAINameJudge" },
      { kind: "phone", start: 7, end: 20, confidence: 1, detector: "PhoneDetector" },
    ],
    mode_used: "hybrid" as const,
    hybrid_failed: false,
    hybrid_failure_code: null,
  };

  async function scanRuleFirst() {
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: TEXT } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));
    await screen.findByRole("textbox", { name: "마스킹된 탐지 결과" });
    fireEvent.keyDown(window, { key: "Escape" });
  }

  it("re-scans the same original text with hybrid when hybrid is picked on the result screen, without resetting", async () => {
    mockScanText.mockResolvedValueOnce(ruleResult).mockResolvedValueOnce(hybridResult);
    await scanRuleFirst();

    expect(screen.getByRole("button", { name: "규칙 전용" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith(TEXT, "hybrid"));
    expect(await screen.findByText(/규칙이 놓친 이름/)).toHaveTextContent("1건");
    expect(screen.getByRole("switch", { name: /이름\(LLM\) 김민준/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "하이브리드 (OpenAI)" })).toHaveAttribute("aria-pressed", "true");
    // 결과 화면은 그대로다 — 초기화되지 않았다.
    expect(screen.getByRole("textbox", { name: "마스킹된 탐지 결과" })).toBeInTheDocument();
  });

  it("can switch back to rule-only from a hybrid result", async () => {
    mockScanText.mockResolvedValueOnce(ruleResult).mockResolvedValueOnce(hybridResult).mockResolvedValueOnce(ruleResult);
    await scanRuleFirst();
    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));
    await screen.findByText(/규칙이 놓친 이름/);

    fireEvent.click(screen.getByRole("button", { name: "규칙 전용" }));

    await waitFor(() => expect(mockScanText).toHaveBeenLastCalledWith(TEXT, "rule"));
    await waitFor(() => expect(screen.queryByText(/규칙이 놓친 이름/)).not.toBeInTheDocument());
    expect(screen.queryByRole("switch", { name: /LLM/ })).not.toBeInTheDocument();
  });

  it("does nothing when the current mode is clicked again", async () => {
    mockScanText.mockResolvedValueOnce(ruleResult);
    await scanRuleFirst();

    fireEvent.click(screen.getByRole("button", { name: "규칙 전용" }));

    expect(mockScanText).toHaveBeenCalledTimes(1);
  });

  it("retries hybrid when it is clicked again after a fallback", async () => {
    mockScanText
      .mockResolvedValueOnce({ ...ruleResult, hybrid_failed: true, hybrid_failure_code: "timeout" })
      .mockResolvedValueOnce(hybridResult);
    render(<DemoPage />);
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));
    fireEvent.change(screen.getByLabelText("탐지할 텍스트 입력"), { target: { value: TEXT } });
    fireEvent.click(screen.getByRole("button", { name: "개인정보 탐지 및 마스킹 하기" }));
    await screen.findByText(/하이브리드 판단에 실패해/);
    fireEvent.keyDown(window, { key: "Escape" });

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));

    await waitFor(() => expect(mockScanText).toHaveBeenCalledTimes(2));
    expect(mockScanText).toHaveBeenLastCalledWith(TEXT, "hybrid");
    expect(await screen.findByText(/규칙이 놓친 이름/)).toBeInTheDocument();
  });

  it("keeps the current result and shows the error when the re-scan request fails", async () => {
    mockScanText.mockResolvedValueOnce(ruleResult).mockRejectedValueOnce(new Error("API 서버에 연결하지 못했습니다."));
    await scanRuleFirst();

    fireEvent.click(screen.getByRole("button", { name: "하이브리드 (OpenAI)" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("API 서버에 연결하지 못했습니다.");
    expect(screen.getByRole("textbox", { name: "마스킹된 탐지 결과" })).toHaveValue("고객 김민준 *************");
  });
});

