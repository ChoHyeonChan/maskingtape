// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { PRESETS } from "../../lib/presets";
import { KIND_LABELS } from "../../types/detection";

interface Props {
  onPick: (text: string) => void;
}

/**
 * 예제 문서를 카드로 한눈에 드러낸다(#455) — 예전엔 예제 2종만 버튼으로 보이고 나머지는
 * "샘플 더 불러오기" 안에 숨어 있어, 처음 온 사람이 어떤 문서 유형을 시험해볼 수 있는지
 * 첫 화면에서 알기 어려웠다. 카드마다 실제로 탐지되는 개인정보 종류를 태그로 붙여, 클릭
 * 전에도 이 예제가 무엇을 보여주는지 짐작할 수 있게 한다.
 */
export function ExampleGallery({ onPick }: Props) {
  return (
    <section className="example-gallery" aria-label="예제 문서로 체험하기">
      <h2>예제로 바로 체험해보기</h2>
      <p className="example-gallery__lead">
        문서 유형을 하나 골라 클릭하면 아래 입력창에 바로 채워집니다 — 실제 개인정보가 아닌 합성 데이터입니다.
      </p>
      <div className="example-gallery__grid">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            className="example-card"
            onClick={() => onPick(preset.text)}
          >
            <span className="example-card__label">{preset.label}</span>
            <span className="example-card__kinds">
              {preset.kinds.map((kind) => (
                <span key={kind} className="example-card__kind-tag">
                  {KIND_LABELS[kind] ?? kind}
                </span>
              ))}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
