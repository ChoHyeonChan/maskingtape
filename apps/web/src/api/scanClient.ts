import type { ScanResponse } from "../types/detection";

/**
 * apps/api README의 POST /scan 계약을 그대로 따른다.
 * 개발 중에는 Vite dev server가 /api/scan을 FastAPI 백엔드의 /scan으로 프록시한다.
 */
export async function scanText(text: string): Promise<ScanResponse> {
  const res = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error ?? `탐지 요청 실패 (HTTP ${res.status})`);
  }

  return res.json();
}
