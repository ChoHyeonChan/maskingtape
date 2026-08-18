import { describe, expect, it, vi } from "vitest";
import { extractTextFromFile } from "./extractText";

function textFile(content: string, name = "notes.txt") {
  return new File([content], name, { type: "text/plain" });
}

describe("extractTextFromFile (#263)", () => {
  it("reads a .txt file's content directly", async () => {
    const file = textFile("고객 홍길동님 연락처 010-1234-5678");
    const result = await extractTextFromFile(file);
    expect(result).toEqual({ ok: true, text: "고객 홍길동님 연락처 010-1234-5678" });
  });

  it("rejects files over the 10MB size limit before reading them", async () => {
    const big = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "big.txt", { type: "text/plain" });
    const result = await extractTextFromFile(big);
    expect(result).toEqual({ ok: false, reason: "too-large" });
  });

  it("rejects unsupported file types", async () => {
    const file = new File(["binary"], "photo.png", { type: "image/png" });
    const result = await extractTextFromFile(file);
    expect(result).toEqual({ ok: false, reason: "unsupported" });
  });

  it("accepts a .txt-like file by extension even without a text/plain MIME type", async () => {
    const file = new File(["메모"], "메모.txt", { type: "" });
    const result = await extractTextFromFile(file);
    expect(result).toEqual({ ok: true, text: "메모" });
  });
});

describe("extractTextFromFile PDF handling (#263)", () => {
  it("joins extracted per-page text and trims the result", async () => {
    vi.doMock("pdfjs-dist", () => ({
      GlobalWorkerOptions: {},
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 2,
          getPage: (pageNumber: number) =>
            Promise.resolve({
              getTextContent: () =>
                Promise.resolve({
                  items:
                    pageNumber === 1
                      ? [{ str: "1페이지" }, { str: "내용" }]
                      : [{ str: "2페이지" }, { str: "내용" }],
                }),
            }),
        }),
      }),
    }));

    const file = new File(["%PDF-fake"], "doc.pdf", { type: "application/pdf" });
    const result = await extractTextFromFile(file);

    expect(result).toEqual({ ok: true, text: "1페이지 내용\n2페이지 내용" });
    vi.doUnmock("pdfjs-dist");
  });

  it("reports 'no-text' for a scanned (image-only) PDF with no extractable text", async () => {
    vi.doMock("pdfjs-dist", () => ({
      GlobalWorkerOptions: {},
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 1,
          getPage: () => Promise.resolve({ getTextContent: () => Promise.resolve({ items: [] }) }),
        }),
      }),
    }));

    const file = new File(["%PDF-fake"], "scanned.pdf", { type: "application/pdf" });
    const result = await extractTextFromFile(file);

    expect(result).toEqual({ ok: false, reason: "no-text" });
    vi.doUnmock("pdfjs-dist");
  });

  it("reports 'parse-error' when the PDF fails to load", async () => {
    vi.doMock("pdfjs-dist", () => ({
      GlobalWorkerOptions: {},
      getDocument: () => ({
        promise: Promise.reject(new Error("corrupt")),
      }),
    }));

    const file = new File(["not a real pdf"], "broken.pdf", { type: "application/pdf" });
    const result = await extractTextFromFile(file);

    expect(result).toEqual({ ok: false, reason: "parse-error" });
    vi.doUnmock("pdfjs-dist");
  });
});
