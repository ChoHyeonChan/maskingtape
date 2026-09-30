// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

export function ClosingCta() {
  return (
    <section className="closing-cta" aria-label="지금 체험하기">
      <h2 className="closing-cta__title">지금 바로 문서를 안전하게 만들어보세요</h2>
      <a className="closing-cta__btn" href="#demo">
        웹 데모 열기 <span aria-hidden="true">→</span>
      </a>
    </section>
  );
}
