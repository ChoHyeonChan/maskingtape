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

      <div className="service-intro__callout" role="note">
        <span className="service-intro__callout-icon" aria-hidden="true">
          !
        </span>
        <div>
          <p className="service-intro__callout-title">왜 마스킹테이프가 더 정확할까요?</p>
          <p className="service-intro__callout-body">
            많은 서비스는 AI(인공지능)에게 통째로 맡겨서, AI가 가끔 헷갈리거나 놓쳐요. 마스킹테이프는 정해진
            규칙으로 먼저 꼼꼼하게 찾고, 애매한 이름만 로컬 LLM으로 한 번 더 확인해요. 그래서{" "}
            <strong>이름을 뺀 나머지 10종(주민번호·전화번호 등)은 규칙만으로 정확도 100%</strong>예요.
          </p>
        </div>
      </div>

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
        웹은 설치 없이 바로 체험, 다운로드는 <code>pip install maskingtape</code> 또는 데스크톱 앱으로 내 PC에서
        실행됩니다.
      </p>

      <p className="service-intro__disclosure">
        파일을 올리면 텍스트 추출은 이 브라우저 안에서 끝나고, 파일 자체는 서버로 전송되지 않습니다. 탐지를
        실행하면 그 텍스트만 저희 API로 보내 처리하며, 서버는 요청 내용을 저장·기록하지 않습니다(무저장·무로그
        원칙) — 그래도 이 데모는 시연·학습용이니 실제 개인정보가 아닌 텍스트로만 확인해 주세요.
      </p>
    </section>
  );
}
