// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { afterEach, describe, expect, it, vi } from "vitest";
import { anonymizeText, scanText } from "./scanClient";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("scanText", () => {
  it("posts the text to /api/scan and returns the parsed detections", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detections: [{ kind: "phone" }] }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await scanText("연락처 010-1234-5678");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/scan",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "연락처 010-1234-5678" }),
      }),
    );
    expect(result).toEqual({ detections: [{ kind: "phone" }] });
  });

  it("sends mode: hybrid only when hybrid is chosen, and passes the mode fields through (#547)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detections: [], mode_used: "rule", hybrid_failed: true, hybrid_failure_code: "timeout" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await scanText("고객 김민준", "hybrid");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/scan",
      expect.objectContaining({ body: JSON.stringify({ text: "고객 김민준", mode: "hybrid" }) }),
    );
    expect(result).toMatchObject({ mode_used: "rule", hybrid_failed: true, hybrid_failure_code: "timeout" });

    await scanText("고객 김민준", "rule");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/scan",
      expect.objectContaining({ body: JSON.stringify({ text: "고객 김민준" }) }),
    );
  });

  it("converts server positions to JS string positions when an emoji comes first (#495)", async () => {
    // 서버는 "😀 연락처 010-1234-5678"에서 전화번호를 코드포인트 6~19로 준다
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detections: [{ kind: "phone", start: 6, end: 19, confidence: 1, detector: "t" }] }),
      ),
    );
    const text = "😀 연락처 010-1234-5678";

    const { detections } = await scanText(text);

    expect(text.slice(detections[0].start, detections[0].end)).toBe("010-1234-5678");
  });
});

describe("anonymizeText (#346)", () => {
  it("posts the text and strategy to /api/anonymize and returns the anonymized text", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ text: "고객 김서준 010-8842-1097", detections: [{ kind: "name" }] }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await anonymizeText("고객 홍길동 010-1234-5678", "pseudonym");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/anonymize",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "고객 홍길동 010-1234-5678", strategy: "pseudonym" }),
      }),
    );
    expect(result.text).toBe("고객 김서준 010-8842-1097");
  });

  it("falls back to the server's message only for statuses the web has no wording for", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ message: "service unavailable." }, 503)));

    await expect(anonymizeText("텍스트", "pseudonym")).rejects.toThrow("service unavailable.");
  });

  // API는 오류마다 영어 message를 담아 보낸다(apps/api errors.py·rate_limit.py). 웹이 아는 상태는
  // 한국어 문구가 먼저여야 방문자에게 "too many requests." 같은 영어가 뜨지 않는다(#759).
  it.each([
    [400, "request body validation failed.", "요청 형식이 올바르지 않습니다. 입력 내용을 확인해 주세요."],
    [413, "text must be at most 100000 characters.", "입력한 텍스트가 너무 깁니다. 내용을 줄인 뒤 다시 시도해 주세요."],
    [429, "too many requests.", "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."],
    [500, "internal server error.", "분석 엔진에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."],
  ])("shows Korean wording instead of the server's English message for HTTP %i (#759)", async (status, serverMessage, shown) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ code: "x", message: serverMessage }, status)));

    await expect(scanText("텍스트")).rejects.toThrow(shown);
  });

  it("reports a connection error when the fetch itself throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(anonymizeText("텍스트", "pseudonym")).rejects.toThrow("서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  });
});
