// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { CoverageSection } from "./components/intro/CoverageSection";
import { ServiceIntro } from "./components/intro/ServiceIntro";
import { ClosingCta } from "./components/layout/ClosingCta";
import { SiteNav } from "./components/layout/SiteNav";

// 랜딩 페이지는 소개(히어로) + 탐지 범위 + 클로징 CTA다 — 실제 입력·결과 체험만 /demo
// 페이지로 옮겨갔다(#553 후속). 그래서 도움말 버튼은 코치마크 대신 /demo로 안내한다:
// 지금 탐지·마스킹을 시연해줄 상태(scanned 등)나 코치마크 자체가 이 페이지엔 없다.
function goToDemo() {
  window.location.href = "/demo";
}

export function App() {
  return (
    <>
      <SiteNav onHelpClick={goToDemo} />
      <div className="app-shell">
        <ServiceIntro />
        <CoverageSection />
        <ClosingCta />
      </div>
    </>
  );
}
