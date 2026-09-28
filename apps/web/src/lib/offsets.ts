// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import type { Detection } from "../types/detection";

/**
 * API의 start·end를 JS 문자열 위치로 바꾼다(#495).
 *
 * API는 위치를 파이썬 문자열 기준(코드포인트)으로 준다(apps/api 계약 "Python 슬라이스 규약").
 * JS 문자열은 UTF-16 코드 유닛이라, 이모지나 확장 B 한자처럼 BMP 밖 글자는 두 칸을 차지한다.
 * 그 위치를 그대로 slice()하면 그런 글자가 k개 앞에 있을 때 가림 구간이 k칸 앞으로 밀리고,
 * 개인정보 끝 k글자가 복사·저장본에 원문으로 남는다. 응답을 받는 자리에서 한 번만 바꾼다.
 */
export function toUtf16Offsets(text: string, detections: Detection[]): Detection[] {
  const units: number[] = [];
  let unit = 0;
  let hasWideChar = false;
  for (const char of text) {
    units.push(unit);
    unit += char.length;
    if (char.length > 1) hasWideChar = true;
  }
  if (!hasWideChar) return detections;
  units.push(unit);

  // 범위를 벗어난 위치는 끝으로 붙인다 — 덜 가리는 쪽으로 틀리지 않게 한다.
  const at = (codePoint: number) => units[Math.min(Math.max(codePoint, 0), units.length - 1)];
  return detections.map((detection) => ({
    ...detection,
    start: at(detection.start),
    end: at(detection.end),
  }));
}
