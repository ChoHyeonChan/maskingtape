// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { ServiceIntro } from "./components/intro/ServiceIntro";
import { ClosingCta } from "./components/layout/ClosingCta";
import { SiteNav } from "./components/layout/SiteNav";

// 랜딩 페이지는 소개(히어로) + 클로징 CTA뿐이다 — 실제 입력·결과 체험은 /demo 페이지로
// 옮겨갔다(#553 후속). 도움말 버튼(코치마크 안내)은 그 페이지에만 있어 여기서는 SiteNav가
// 아예 렌더링하지 않는다.
export function App() {
  return (
    <>
      <SiteNav />
      <div className="app-shell">
        <ServiceIntro />
        <ClosingCta />
      </div>
    </>
  );
}
