/** core의 Detection과 1:1 대응 (apps/api README의 /scan, /anonymize 계약 스키마). */
export interface Detection {
  kind: string;
  start: number;
  end: number;
  text: string;
  confidence: number;
  detector: string;
}

export interface ScanResponse {
  detections: Detection[];
}

/** 요약·범례에서 종류를 나열하는 고정 순서 (KIND_LABELS/KIND_COLORS의 삽입 순서에 의존하지 않도록 명시). */
export const KIND_ORDER = ["rrn", "phone", "email", "address", "name"] as const;

/** kind별 한국어 표시명 — core anonymizers/label.py의 DEFAULT_LABELS와 동일하게 맞춘다. */
export const KIND_LABELS: Record<string, string> = {
  rrn: "주민등록번호",
  phone: "전화번호",
  email: "이메일",
  name: "이름",
  address: "주소",
};

/** kind별 강조 색상 — dataviz 스킬 카테고리 팔레트 슬롯 1~5(고정 순서, CVD 검증 완료). */
export const KIND_COLORS: Record<string, string> = {
  rrn: "var(--kind-rrn)",
  phone: "var(--kind-phone)",
  email: "var(--kind-email)",
  address: "var(--kind-address)",
  name: "var(--kind-name)",
};
