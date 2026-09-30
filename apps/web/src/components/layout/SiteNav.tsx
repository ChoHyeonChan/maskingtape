// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState } from "react";

interface Props {
  /** 도움말 버튼(정확도 안내 말풍선 포함)은 /demo 페이지에만 있다 — 코치마크·스캔 상태
   * 자체가 그 페이지에만 있어서다. 다른 페이지에서는 이 prop 자체가 쓰이지 않는다. */
  onHelpClick?: () => void;
  hasResult?: boolean;
  coachMarkActive?: boolean;
  /** "accuracy"/"demo"는 /accuracy·/demo처럼 랜딩과 분리된 하위 페이지에서 쓴다 — 소개
   * 링크가 앵커(#id)가 아니라 랜딩으로 돌아가는 절대경로를 가리키고, 그 페이지 자신을
   * 가리키는 nav 항목은 강조 표시된다. */
  variant?: "home" | "accuracy" | "demo";
}

const ACCURACY_BUBBLE_TIMEOUT_MS = 30_000;

export function SiteNav({ onHelpClick, hasResult = false, coachMarkActive = false, variant = "home" }: Props) {
  const isDemo = variant === "demo";
  const isHome = variant === "home";
  const brandHref = isHome ? "#intro" : "/";
  const introHref = isHome ? "#intro" : "/#intro";
  // 탐지 범위(무엇을 잡나요)는 랜딩 페이지에 있다 — 랜딩 안에서는 그냥 앵커, 다른
  // 페이지에서는 랜딩으로 돌아가는 절대경로다.
  const coverageHref = isHome ? "#coverage" : "/#coverage";
  // 체험하기(입력·결과 패널)만 /demo 페이지에 있다(#553 후속) — 어디서 보든 항상 그
  // 실제 경로로 이동한다.
  const demoHref = "/demo";
  const isDemoActive = variant === "demo";
  // 정확도 안내(예전엔 맨 아래 footer에만 있었다)를 도움말 버튼 옆에도 잠깐 띄워서, 처음
  // 쓰는 사람이 스크롤해서 맨 아래까지 안 내려도 "규칙 기반이라 이름을 놓칠 수 있다"는 걸
  // 바로 알게 한다. 예전엔 아무 데나 클릭해도 닫혔는데, 그러면 텍스트를 입력하거나 탐지
  // 결과를 보려고 클릭하는 순간 바로 사라져서 정작 결과 화면까지는 못 보고 닫혀버렸다 —
  // 이제는 30초 뒤 자동으로 사라지거나, 말풍선의 X 버튼을 눌러야만 닫힌다.
  const [showAccuracyBubble, setShowAccuracyBubble] = useState(true);
  const wasResult = useRef(false);

  useEffect(() => {
    if (!showAccuracyBubble) return;

    const timeout = window.setTimeout(() => setShowAccuracyBubble(false), ACCURACY_BUBBLE_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, [showAccuracyBubble]);

  // 처음 페이지에서 30초 안에 못 보고 지나쳤다면, 정작 결과를 확인하는 시점(놓친 이름이
  // 있을까 궁금해질 때)엔 이미 사라져 있었다 — 탐지 결과가 막 나온 순간에도 다시 띄워준다.
  useEffect(() => {
    if (hasResult && !wasResult.current) {
      setShowAccuracyBubble(true);
    }
    wasResult.current = hasResult;
  }, [hasResult]);

  return (
    <nav className="site-nav" aria-label="주요 섹션 이동">
      <div className="site-nav__inner">
        <a className="site-nav__brand" href={brandHref} aria-label="맨 위로">
          <img
            src="/maskingtape-logo-blue.png"
            alt="MaskingTape"
            width={1501}
            height={276}
          />
        </a>

        <div className="site-nav__links">
          <a className="site-nav__link" href={introHref}>
            소개
          </a>
          <a className="site-nav__link" href={coverageHref}>
            탐지 범위
          </a>
          <a
            className={variant === "accuracy" ? "site-nav__link site-nav__link--active" : "site-nav__link"}
            href="/accuracy"
          >
            정확도
          </a>
          <a
            className={isDemoActive ? "site-nav__link site-nav__link--active" : "site-nav__link"}
            href={demoHref}
          >
            체험하기
          </a>
          <a
            className="site-nav__link"
            href="https://github.com/ChoHyeonChan/maskingtape"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </div>

        <div className="site-nav__actions">
          <a
            className="site-nav__doc-link"
            href="https://github.com/ChoHyeonChan/maskingtape/blob/main/THIRD_PARTY_NOTICES.md"
            target="_blank"
            rel="noopener noreferrer"
          >
            오픈소스 라이선스
          </a>

          {/* 도움말 버튼(정확도 안내 말풍선 포함)은 체험하기(/demo) 페이지에서만 뜬다 —
              코치마크·스캔 상태가 그 페이지에만 있어서, 다른 페이지에서는 눌러도 안내할
              게 없다. */}
          {isDemo && (
            <div className="help-button-wrap">
              <button
                type="button"
                className="help-button"
                aria-label="사용 안내 다시 보기"
                data-tooltip="도움말"
                onClick={onHelpClick}
              >
                i
              </button>

              {/* 코치마크 오버레이가 떠 있는 동안엔 숨긴다 — 코치마크의 빨간 "아무 데나 누르면
                  닫힙니다" 힌트와 이 말풍선이 같은 배색이라 겹쳐 보이면 서로 다른 안내인지
                  구분이 안 된다. 코치마크가 닫히면 남은 타이머·닫기 상태 그대로 다시 보인다. */}
              {showAccuracyBubble && !coachMarkActive && (
                <div className="accuracy-bubble" role="status">
                  <button
                    type="button"
                    className="accuracy-bubble__close"
                    aria-label="정확도 안내 닫기"
                    onClick={() => setShowAccuracyBubble(false)}
                  >
                    ×
                  </button>
                  <p>
                    규칙 기반 탐지라 이름 일부를 놓칠 수 있어요 — <strong>정확한 결과가 필요하면 로컬 설치를
                    권장합니다.</strong>
                  </p>
                </div>
              )}
            </div>
          )}

          <a className="site-nav__cta" href={demoHref}>
            웹에서 체험하기
          </a>
        </div>
      </div>
    </nav>
  );
}
