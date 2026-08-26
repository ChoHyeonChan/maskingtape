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

  it("surfaces the server's error message when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ message: "요청이 너무 큽니다." }, 413)));

    await expect(anonymizeText("x".repeat(200_000), "pseudonym")).rejects.toThrow("요청이 너무 큽니다.");
  });

  it("reports a connection error when the fetch itself throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(anonymizeText("텍스트", "pseudonym")).rejects.toThrow("API 서버에 연결하지 못했습니다");
  });
});
