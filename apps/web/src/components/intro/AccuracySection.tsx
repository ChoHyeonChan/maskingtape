// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

// README.md "정확도 (공개 벤치마크)" 표와 같은 수치다(#455) — 측정 방식이 바뀌면
// README와 함께 갱신한다. 자체 합성 데이터셋(규칙 전용 모드) 기준.
const ROWS: { label: string; precision: string; recall: string; f1: string }[] = [
  { label: "주민등록번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "전화번호(휴대폰+유선+050X)", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "이메일", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "주소", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "신용카드번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "사업자등록번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "여권번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "계좌번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "생년월일", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "운전면허번호", precision: "1.000", recall: "1.000", f1: "1.000" },
  { label: "이름 (규칙 전용)", precision: "0.954", recall: "0.869", f1: "0.910" },
];

const OVERALL = { precision: "0.983", recall: "0.950", f1: "0.966" };

export function AccuracySection() {
  return (
    <section className="accuracy-section" aria-label="정확도">
      <h2>얼마나 정확한가요</h2>
      <p className="accuracy-section__lead">
        저작권·개인정보 걱정 없는 자체 합성 데이터셋(500건, 규칙 전용 모드)으로 측정했습니다 — 같은 수치를{" "}
        <a
          href="https://github.com/ChoHyeonChan/maskingtape/blob/main/README.md"
          target="_blank"
          rel="noopener noreferrer"
        >
          README
        </a>
        의 "정확도 (공개 벤치마크)" 절에서도 확인할 수 있습니다.
      </p>
      <div className="accuracy-section__table-wrap">
        <table className="accuracy-section__table">
          <thead>
            <tr>
              <th scope="col">종류</th>
              <th scope="col">precision</th>
              <th scope="col">recall</th>
              <th scope="col">F1</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td>{row.precision}</td>
                <td>{row.recall}</td>
                <td>{row.f1}</td>
              </tr>
            ))}
            <tr className="accuracy-section__overall">
              <th scope="row">전체</th>
              <td>{OVERALL.precision}</td>
              <td>{OVERALL.recall}</td>
              <td>{OVERALL.f1}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="accuracy-section__caveat">
        이름은 문맥 단서가 없으면 규칙만으로 놓칠 수 있습니다(재현율 0.869) — 로컬 LLM(<code>--llm</code>)을 켜면
        F1 0.923까지 올라갑니다. 자세한 측정 조건과 한계는 README를 참고하세요.
      </p>
    </section>
  );
}
