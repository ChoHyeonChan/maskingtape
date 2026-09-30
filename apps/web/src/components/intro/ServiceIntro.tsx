// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

export function ServiceIntro() {
  return (
    <section className="service-intro" id="intro" aria-label="서비스 소개">
      <span className="service-intro__eyebrow">한국어 개인정보 비식별화 · 오픈소스 엔진</span>
      <h2 className="service-intro__headline">
        공유하기 전,
        <br />
        내 정보부터 가려보세요
      </h2>
      <p className="service-intro__lead">
        글 속 이름, 전화번호, 주소를 찾아 가려드려요.
        <br />
        개인정보는 가리고, 필요한 내용만 편하게 공유하세요.
      </p>

      <div className="service-intro__actions">
        <a className="service-intro__btn service-intro__btn--primary" href="#demo">
          지금 체험하기 <span aria-hidden="true">→</span>
        </a>
        <a
          className="service-intro__btn service-intro__btn--ghost"
          href="https://github.com/ChoHyeonChan/maskingtape/releases"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span aria-hidden="true">⬇</span> 다운로드
        </a>
      </div>
      <p className="service-intro__hint">
        바로 실행하면 웹에서 설치 없이 바로 체험 가능하고 다운로드는 <code>pip install maskingtape</code> 또는
        데스크톱 앱으로 내 PC에서 실행됩니다.
      </p>
    </section>
  );
}
