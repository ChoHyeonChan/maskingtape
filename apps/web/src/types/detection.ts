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

export const KIND_ORDER = [
  "rrn",
  "passport",
  "driver_license",
  "phone",
  "email",
  "card",
  "account",
  "address",
  "name",
  "birth_date",
  "biz_reg",
] as const;

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
