// SPDX-License-Identifier: Apache-2.0

/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { extractTextFromFile } from "./extractText";

function textFile(content: string, name = "notes.txt") {
  return new File([content], name, { type: "text/plain" });
}

// apps/desktop/demo/의 실제 데모 파일로 회귀를 고정한다(#407 완료 기준) — 데스크톱이
// 지원하는 형식(csv/tsv/md/json/log)을 웹도 그대로 읽어야 한다. 이 파일은 src/ 아래라
// tsconfig.app.json의 제한된 types 적용을 받는데, 삼중 슬래시 참조로 node 전역을
// 이 파일에서만 명시적으로 끌어온다(reducedMotion.test.ts와 동일한 패턴, #189).
const DEMO_DIR = join(process.cwd(), "..", "desktop", "demo");
function readDemoFile(name: string, mime: string): File {
  const content = readFileSync(join(DEMO_DIR, name), "utf-8");
  return new File([content], name, { type: mime });
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

describe("extractTextFromFile matches desktop's supported formats (#407)", () => {
  it.each([
    ["02_거래처명단.csv", "text/csv"],
    ["03_출장신청서.md", "text/markdown"],
    ["04_가입신청.json", "application/json"],
  ])("reads the real %s demo file used for the submission demo", async (name, mime) => {
    const file = readDemoFile(name, mime);
    const result = await extractTextFromFile(file);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.text.length).toBeGreaterThan(0);
      expect(result.text).toBe(readFileSync(join(DEMO_DIR, name), "utf-8"));
    }
  });

  it("reads a .tsv file the same way as .txt (no desktop demo file, but same code path)", async () => {
    const file = new File(["이름\t연락처\n홍길동\t010-1234-5678"], "명단.tsv", { type: "text/tab-separated-values" });
    const result = await extractTextFromFile(file);
    expect(result).toEqual({ ok: true, text: "이름\t연락처\n홍길동\t010-1234-5678" });
  });

  it("reads a .log file the same way as .txt", async () => {
    const file = new File(["2026-08-01 접속 010-1234-5678"], "access.log", { type: "text/plain" });
    const result = await extractTextFromFile(file);
    expect(result).toEqual({ ok: true, text: "2026-08-01 접속 010-1234-5678" });
  });

  it("falls back to the extension when the browser reports an empty file.type for .csv/.md", async () => {
    const csv = new File(["a,b\n1,2"], "no-mime.csv", { type: "" });
    const md = new File(["# 제목"], "no-mime.md", { type: "" });
    expect(await extractTextFromFile(csv)).toEqual({ ok: true, text: "a,b\n1,2" });
    expect(await extractTextFromFile(md)).toEqual({ ok: true, text: "# 제목" });
  });
});
