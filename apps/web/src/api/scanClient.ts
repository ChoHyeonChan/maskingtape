import type { ScanResponse } from "../types/detection";

interface ApiErrorBody {
  code?: string;
  message?: string;
}

const ERROR_MESSAGES: Record<number, string> = {
  400: "요청 형식이 올바르지 않습니다. 입력 내용을 확인해 주세요.",
  413: "입력한 텍스트가 너무 깁니다. 내용을 줄인 뒤 다시 시도해 주세요.",
  500: "분석 엔진에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
  502: "API 서버에 연결하지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.",
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let res: Response;

  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("API 서버에 연결하지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.");
  }

  if (!res.ok) {
    const errorBody = (await res.json().catch(() => null)) as ApiErrorBody | null;
    throw new Error(
      errorBody?.message ?? errorBody?.code ?? ERROR_MESSAGES[res.status] ?? `요청 실패 (HTTP ${res.status})`,
    );
  }

  return res.json();
}

/**
 * During development, Vite proxies /api/scan to the FastAPI backend's /scan route.
 */
export function scanText(text: string): Promise<ScanResponse> {
  return postJson<ScanResponse>("/api/scan", { text });
}
