// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import type { Detection } from "../types/detection";

/** 웹 데모 탐지 모드(#547). 기본은 규칙 전용이고, 하이브리드는 사용자가 고를 때만 쓴다. */
export type DetectionMode = "rule" | "hybrid";

/**
 * 서버(apps/api)의 하이브리드 입력 상한 기본값(`MASKINGTAPE_API_HYBRID_MAX_TEXT_LENGTH`)과 같다.
 * 넘으면 서버가 어차피 규칙 결과로 돌려보내므로, 화면에서 먼저 하이브리드 선택을 막고 이유를 보여 준다.
 */
export const HYBRID_MAX_TEXT_LENGTH = 5_000;

/**
 * 하이브리드 성공 시 OpenAI 판단기가 더 찾은 이름은 `detector`가 판단기 클래스 이름으로 온다
 * (apps/api `core_adapter._name_detections_from_judge`). 규칙 탐지기는 core의 `…Detector` 이름이다.
 */
const LLM_DETECTORS = new Set(["OpenAINameJudge"]);

export function isLlmDetection(detection: Detection): boolean {
  return LLM_DETECTORS.has(detection.detector);
}

/** 하이브리드가 실패해 규칙 결과로 돌아왔을 때 화면에 보여 줄 이유. 코드는 apps/api가 정한다. */
const FAILURE_MESSAGES: Record<string, string> = {
  name_judge_unavailable: "지금 서버에 하이브리드 판단기가 연결돼 있지 않습니다.",
  input_too_long: `하이브리드 입력 상한(${HYBRID_MAX_TEXT_LENGTH.toLocaleString()}자)을 넘었습니다.`,
  rate_limited: "하이브리드 요청이 많아 잠시 제한됐습니다. 잠시 후 다시 시도해 주세요.",
  spend_limit: "이번 달 하이브리드 사용 한도를 모두 썼습니다.",
  timeout: "판단기 응답이 늦어 시간이 초과됐습니다.",
  network: "판단기에 연결하지 못했습니다.",
};

const DEFAULT_FAILURE_MESSAGE = "판단기 응답을 처리하지 못했습니다.";

export function hybridFailureMessage(code: string | null | undefined): string {
  return (code && FAILURE_MESSAGES[code]) || DEFAULT_FAILURE_MESSAGE;
}

/** 한 번의 탐지에서 고른 모드와 실제로 쓰인 모드. 화면 알림과 가명처리 재요청이 이 값을 본다. */
export interface ScanModeInfo {
  requested: DetectionMode;
  used: DetectionMode;
  failureCode: string | null;
}

/** 서버 응답에서 모드 정보를 꺼낸다. 필드가 없으면(옛 서버) 규칙 전용으로 본다. */
export function readModeInfo(
  requested: DetectionMode,
  response: { mode_used?: DetectionMode; hybrid_failed?: boolean; hybrid_failure_code?: string | null },
): ScanModeInfo {
  const used = response.mode_used ?? "rule";
  const failed = requested === "hybrid" && (response.hybrid_failed === true || used !== "hybrid");
  return { requested, used, failureCode: failed ? (response.hybrid_failure_code ?? null) : null };
}

export function hybridFellBack(info: ScanModeInfo): boolean {
  return info.requested === "hybrid" && info.used !== "hybrid";
}
