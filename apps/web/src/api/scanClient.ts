import type { ScanResponse } from "../types/detection";

/**
 * apps/api README의 POST /scan 계약을 그대로 따른다.
 * 지금은 dev-server/scanProxyPlugin.ts(core CLI 호출)가 이 요청을 받는다 —
 * 기태의 apps/api가 완성되면 프록시만 실제 API로 바뀌고 이 함수는 그대로 쓴다.
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
