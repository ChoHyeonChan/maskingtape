import { afterEach, describe, expect, it, vi } from "vitest";
import { scanText } from "./scanClient";

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
