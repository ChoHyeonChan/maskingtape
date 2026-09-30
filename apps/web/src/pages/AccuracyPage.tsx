// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { SiteNav } from "../components/layout/SiteNav";

// README·AccuracySection의 종류별 표와 같은 수치다(#455) — 이름을 뺀 10종은 전부
// precision/recall/F1 = 1.000이라 여기서는 F1만 백분율로 보여준다. AccuracySection의
// ROWS가 바뀌면 이 배열도 함께 갱신한다.
const PERFECT_KINDS: { label: string; color: string }[] = [
  { label: "주민등록번호", color: "var(--kind-rrn)" },
  { label: "전화번호", color: "var(--kind-phone)" },
  { label: "이메일", color: "var(--kind-email)" },
  { label: "주소", color: "var(--kind-address)" },
  { label: "신용카드번호", color: "var(--kind-card)" },
  { label: "사업자등록번호", color: "var(--kind-business)" },
  { label: "여권번호", color: "var(--kind-passport)" },
  { label: "계좌번호", color: "var(--kind-fallback)" },
  { label: "생년월일", color: "var(--kind-fallback)" },
  { label: "운전면허번호", color: "var(--kind-fallback)" },
];

function goHome() {
  window.location.href = "/";
}

export function AccuracyPage() {
  return (
    <>
      <SiteNav variant="accuracy" onHelpClick={goHome} />
      <div className="accuracy-page">
        <section className="accuracy-hero" aria-label="전체 정확도">
          <div className="accuracy-hero__eyebrow">정확도, 숨기지 않고 다 보여드려요</div>
          <h1 className="accuracy-hero__title">
            정말로 얼마나 정확한지,
            <br />
            있는 그대로 알려드릴게요
          </h1>

          <div className="accuracy-hero__card">
            <div className="accuracy-hero__stat">
              <div className="accuracy-hero__stat-value">
                96.6<span>%</span>
              </div>
              <div className="accuracy-hero__stat-label">전체 F1 점수</div>
            </div>
            <div className="accuracy-hero__divider" aria-hidden="true" />
            <div className="accuracy-hero__stat accuracy-hero__stat--wide">
              <div className="accuracy-hero__stat-plain">
                쉽게 말하면,
                <br />
                100건 중 약 97건을 정확히 처리해요
              </div>
            </div>
            <div className="accuracy-hero__divider" aria-hidden="true" />
            <div className="accuracy-hero__stat">
              <div className="accuracy-hero__stat-plain">이름 뺀 10종</div>
              <div className="accuracy-hero__stat-sub">규칙만으로 정확도 100%</div>
            </div>
          </div>
        </section>

        <section className="accuracy-why" aria-label="왜 더 정확한가">
          <h2 className="accuracy-section-title">왜 마스킹테이프가 더 정확할까요?</h2>
          <p className="accuracy-section-lead">다른 서비스와 다르게, 두 단계를 거쳐서 찾아요</p>

          <div className="accuracy-callout" role="note">
            <span className="accuracy-callout__icon" aria-hidden="true">
              !
            </span>
            <p className="accuracy-callout__body">
              <strong>
                많은 서비스는 AI(인공지능)에게 통째로 맡겨서, AI가 가끔 헷갈리거나 놓쳐요. 마스킹테이프는 정해진
                규칙으로 먼저 꼼꼼하게 찾고, 애매한 이름만 로컬 LLM으로 한 번 더 확인해요.
              </strong>{" "}
              그래서 이름을 뺀 나머지 10종(주민번호·전화번호 등)은 규칙만으로 정확도 100%예요.
            </p>
          </div>

          <div className="accuracy-steps">
            <div className="accuracy-step">
              <div className="accuracy-step__badge" aria-hidden="true">
                1
              </div>
              <div className="accuracy-step__title">정해진 규칙으로 먼저 꼼꼼하게 찾기</div>
              <p className="accuracy-step__body">
                주민번호·전화번호·카드번호처럼 <strong>형식이 정해진 10종</strong>은 규칙(정규식·사전)만으로
                놓치지 않고 찾아요.
              </p>
            </div>

            <div className="accuracy-step__arrow" aria-hidden="true">
              →
            </div>

            <div className="accuracy-step">
              <div className="accuracy-step__badge" aria-hidden="true">
                2
              </div>
              <div className="accuracy-step__title">애매한 이름만 로컬 LLM이 한 번 더 확인</div>
              <p className="accuracy-step__body">
                이름은 정해진 형식이 없어 규칙만으로는 가끔 놓쳐요. 애매한 경우만{" "}
                <strong>내 컴퓨터 안의 로컬 LLM</strong>이 문맥을 보고 다시 확인해요.
              </p>
            </div>
          </div>
        </section>

        <section className="accuracy-glossary" aria-label="쉬운 용어 설명">
          <h2 className="accuracy-section-title">헷갈리는 용어, 쉽게 풀어드릴게요</h2>
          <p className="accuracy-section-lead">아래 표에 나오는 세 단어만 알면 숫자가 쉽게 읽혀요</p>

          <div className="accuracy-glossary__grid">
            <div className="accuracy-glossary__card">
              <div className="accuracy-glossary__badge">P</div>
              <div className="accuracy-glossary__term">정밀도 (Precision)</div>
              <p className="accuracy-glossary__body">
                "가렸다"고 한 것 중, <strong>진짜 개인정보였던 비율</strong>이에요. 즉, 엉뚱한 곳을 잘못 가리지는
                않았는지 보는 값이에요.
              </p>
            </div>
            <div className="accuracy-glossary__card">
              <div className="accuracy-glossary__badge">R</div>
              <div className="accuracy-glossary__term">재현율 (Recall)</div>
              <p className="accuracy-glossary__body">
                문서에 <strong>실제로 있던 개인정보 중, 몇 개나 찾아냈는지</strong>의 비율이에요. 즉, 놓친 게
                없는지 보는 값이에요.
              </p>
            </div>
            <div className="accuracy-glossary__card">
              <div className="accuracy-glossary__badge">F1</div>
              <div className="accuracy-glossary__term">F1 점수</div>
              <p className="accuracy-glossary__body">
                정밀도와 재현율을 <strong>함께 고려한 종합 점수</strong>예요. 둘 중 하나만 좋아서는 F1도 높아지지
                않아요.
              </p>
            </div>
          </div>
        </section>

        <section className="accuracy-breakdown" aria-label="종류별 정확도">
          <h2 className="accuracy-section-title">종류별로 자세히 볼까요?</h2>
          <p className="accuracy-section-lead">
            막대가 끝까지 채워질수록 더 정확하게 찾아냈다는 뜻이에요 (F1 점수 기준)
          </p>

          <div className="accuracy-breakdown__list">
            {PERFECT_KINDS.map((kind) => (
              <div className="accuracy-row" key={kind.label}>
                <div className="accuracy-row__label">
                  <span className="accuracy-row__dot" style={{ background: kind.color }} />
                  <span>{kind.label}</span>
                </div>
                <div className="accuracy-row__track">
                  <div className="accuracy-row__fill" style={{ width: "100%", background: kind.color }} />
                </div>
                <div className="accuracy-row__value" style={{ color: kind.color }}>
                  100%
                </div>
              </div>
            ))}

            {/* 이름: 유일하게 100%가 아닌 항목이라 카드를 다르게 강조하고, 규칙만 vs 로컬 LLM
                두 막대로 비교해 보여준다(README·AccuracySection 캐비엇과 같은 수치). */}
            <div className="accuracy-name-card">
              <div className="accuracy-name-card__head">
                <span className="accuracy-row__dot" style={{ background: "var(--kind-name)" }} />
                <span className="accuracy-name-card__title">이름</span>
                <span className="accuracy-name-card__badge">유일하게 100%가 아닌 항목</span>
              </div>

              <div className="accuracy-row accuracy-row--compact">
                <span className="accuracy-row__sublabel">규칙만 사용</span>
                <div className="accuracy-row__track">
                  <div className="accuracy-row__fill accuracy-row__fill--muted" style={{ width: "91%" }} />
                </div>
                <div className="accuracy-row__value accuracy-row__value--muted">91.0%</div>
              </div>
              <div className="accuracy-row accuracy-row--compact">
                <span className="accuracy-row__sublabel">+ 로컬 LLM</span>
                <div className="accuracy-row__track">
                  <div
                    className="accuracy-row__fill"
                    style={{ width: "92.3%", background: "var(--kind-name)" }}
                  />
                </div>
                <div className="accuracy-row__value" style={{ color: "var(--kind-name)" }}>
                  92.3%
                </div>
              </div>

              <p className="accuracy-name-card__note">
                이름은 정해진 형식이 없어서, 문맥 단서가 부족하면 규칙만으로 가끔 놓쳐요(재현율 0.869). 로컬
                LLM을 함께 켜면 F1 0.910 → <strong>0.923</strong>까지 올라가요.
              </p>
            </div>
          </div>
        </section>

        <section className="accuracy-footnote">
          <p>
            저작권·개인정보 걱정 없는 자체 합성 데이터셋(500건, 규칙 전용 모드)으로 측정했습니다 — 같은 수치를{" "}
            <a
              href="https://github.com/ChoHyeonChan/maskingtape/blob/main/README.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              README
            </a>
            의 "정확도 (공개 벤치마크)" 절에서도 확인할 수 있습니다. 자세한 측정 조건과 한계도 README를 참고해
            주세요.
          </p>
        </section>
      </div>
    </>
  );
}
