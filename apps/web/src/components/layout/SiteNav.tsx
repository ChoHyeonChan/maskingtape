// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

const SECTION_LINKS = [
  { href: "#intro", label: "소개" },
  { href: "#coverage", label: "탐지 범위" },
  { href: "#accuracy", label: "정확도" },
  { href: "#demo", label: "체험하기" },
];

export function SiteNav() {
  return (
    <nav className="site-nav" aria-label="주요 섹션 이동">
      <div className="site-nav__inner">
        <a className="site-nav__brand" href="#intro" aria-label="맨 위로">
          <img src="/maskingtape-logo-blue.png" alt="MaskingTape" width={1501} height={276} />
        </a>

        <div className="site-nav__links">
          {SECTION_LINKS.map((link) => (
            <a key={link.href} className="site-nav__link" href={link.href}>
              {link.label}
            </a>
          ))}
          <a
            className="site-nav__link"
            href="https://github.com/ChoHyeonChan/maskingtape"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </div>

        <a className="site-nav__cta" href="#demo">
          웹에서 체험하기
        </a>
      </div>
    </nav>
  );
}
