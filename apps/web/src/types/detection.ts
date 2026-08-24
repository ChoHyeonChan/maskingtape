/** Public detection shape returned by apps/api /scan and /anonymize. */
export interface Detection {
  kind: string;
  start: number;
  end: number;
  confidence: number;
  detector: string;
}

export interface ScanResponse {
  detections: Detection[];
}

/** POST /anonymize 응답 — strategy에 따라 비식별화까지 끝난 text를 함께 돌려준다(#346). */
export interface AnonymizeResponse {
  text: string;
  detections: Detection[];
}

export const KIND_LABELS: Record<string, string> = {
  rrn: "주민등록번호",
  passport: "여권번호",
  driver_license: "운전면허",
  phone: "전화번호",
  email: "이메일",
  card: "카드번호",
  account: "계좌번호",
  name: "이름",
  address: "주소",
  birth_date: "생년월일",
  biz_reg: "사업자등록번호",
  business_registration: "사업자등록번호",
};

/** 오른쪽 목록의 항목에 마우스를 올렸을 때 왼쪽 "마스킹 결과" 텍스트에서 강조할 범위. */
export interface HighlightRange {
  start: number;
  end: number;
  color: string;
}

export const KIND_COLORS: Record<string, string> = {
  rrn: "var(--kind-rrn)",
  passport: "var(--kind-passport)",
  phone: "var(--kind-phone)",
  email: "var(--kind-email)",
  card: "var(--kind-card)",
  address: "var(--kind-address)",
  name: "var(--kind-name)",
  biz_reg: "var(--kind-business)",
  business_registration: "var(--kind-business)",
};
