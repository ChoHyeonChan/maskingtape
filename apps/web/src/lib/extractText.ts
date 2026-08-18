const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB — 브라우저에서 PDF 파싱이 느려지지 않게 상한을 둔다.

export type ExtractFailureReason = "unsupported" | "too-large" | "no-text" | "parse-error";

export type ExtractResult = { ok: true; text: string } | { ok: false; reason: ExtractFailureReason };

export const EXTRACT_ERROR_MESSAGES: Record<ExtractFailureReason, string> = {
  unsupported: "지원하지 않는 파일 형식입니다. .txt 또는 텍스트 PDF 파일을 올려주세요.",
  "too-large": "파일이 너무 큽니다. 10MB 이하 파일을 올려주세요.",
  "no-text": "이 PDF에서 텍스트를 찾지 못했습니다. 스캔본(이미지) PDF는 지원하지 않습니다 — 텍스트 PDF만 지원합니다.",
  "parse-error": "파일을 읽는 중 오류가 발생했습니다. 파일이 손상되지 않았는지 확인해 주세요.",
};

/**
 * 파일에서 텍스트만 추출한다 — 파일 자체는 절대 서버로 보내지 않는다(#263).
 * 서버로 파일을 올리면 개인정보가 서버를 거치게 되어 무저장·무로그 원칙이 깨지므로,
 * 추출까지 전부 브라우저 안에서 끝내고 결과 텍스트만 기존 /api/scan 흐름에 태운다.
 */
export async function extractTextFromFile(file: File): Promise<ExtractResult> {
  if (file.size > MAX_FILE_SIZE) return { ok: false, reason: "too-large" };

  const name = file.name.toLowerCase();
  if (name.endsWith(".txt") || file.type === "text/plain") {
    try {
      const text = await file.text();
      return { ok: true, text };
    } catch {
      return { ok: false, reason: "parse-error" };
    }
  }

  if (name.endsWith(".pdf") || file.type === "application/pdf") {
    return extractPdfText(file);
  }

  return { ok: false, reason: "unsupported" };
}

async function extractPdfText(file: File): Promise<ExtractResult> {
  try {
    const pdfjs = await import("pdfjs-dist");
    pdfjs.GlobalWorkerOptions.workerSrc = new URL(
      "pdfjs-dist/build/pdf.worker.min.mjs",
      import.meta.url,
    ).toString();

    const buffer = await file.arrayBuffer();
    const doc = await pdfjs.getDocument({ data: buffer }).promise;

    const pageTexts: string[] = [];
    for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber += 1) {
      const page = await doc.getPage(pageNumber);
      const content = await page.getTextContent();
      const pageText = content.items.map((item) => ("str" in item ? item.str : "")).join(" ");
      pageTexts.push(pageText);
    }

    const text = pageTexts.join("\n").trim();
    if (!text) return { ok: false, reason: "no-text" };
    return { ok: true, text };
  } catch {
    return { ok: false, reason: "parse-error" };
  }
}
