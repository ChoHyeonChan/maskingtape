// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

export function ServiceIntro() {
  return (
    <section className="service-intro" aria-label="서비스 소개">
      <h2>이게 어떤 서비스인가요</h2>
      <p>
        <strong>maskingtape</strong>는 한국어 문서 속 개인정보를 찾아 마스킹·가명처리하는 오픈소스 엔진입니다.
        정규식·사전 기반 규칙과 로컬 LLM(Ollama)을 함께 써서, 문맥 단서가 있는 이름처럼 규칙만으로 놓치기 쉬운
        표현까지 잡습니다.
      </p>
      <p>
        파일을 올리면 텍스트 추출은 이 브라우저 안에서 끝나고, 파일 자체는 서버로 전송되지 않습니다. 탐지를
        실행하면 그 텍스트만 저희 API로 보내 처리하며, 서버는 요청 내용을 저장·기록하지 않습니다(무저장·무로그
        원칙) — 그래도 이 데모는 시연·학습용이니 실제 개인정보가 아닌 텍스트로만 확인해 주세요.
      </p>
    </section>
  );
}
