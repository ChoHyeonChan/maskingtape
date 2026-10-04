// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from "react";
import { ExampleGallery } from "../intro/ExampleGallery";

interface Props {
  onPick: (text: string) => void;
  onClose: () => void;
}

// 예제 갤러리는 원래 페이지 위쪽의 큰 섹션이었다 — 이제는 "문서 입력" 패널의 샘플 버튼을
// 눌러야만 뜨는 팝업으로 옮겨서, 메인 화면 자체에는 더 이상 보이지 않는다. 내용(카드 목록)은
// ExampleGallery를 그대로 재사용해 두 군데서 같은 로직을 유지보수하지 않게 한다.
export function SamplePickerModal({ onPick, onClose }: Props) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function handlePick(text: string) {
    onPick(text);
    onClose();
  }

  return (
    <div className="sample-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="sample-modal"
        role="dialog"
        aria-modal="true"
        aria-label="샘플 문서 고르기"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="sample-modal__close" aria-label="닫기" onClick={onClose}>
          ×
        </button>
        <div className="sample-modal__body">
          <ExampleGallery onPick={handlePick} />
        </div>
      </div>
    </div>
  );
}
