/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// jsdom은 스타일시트 기반 CSS를 실제로 계산하지 않아 getComputedStyle로는
// 애니메이션 동작을 검증할 수 없다. 대신 prefers-reduced-motion 규칙 자체가
// 실수로 지워지지 않는지 파일 내용으로 지킨다(#189). 실제 브라우저 동작 검증은
// Playwright로 별도 수행했다.
//
// 이 파일은 src/ 아래라 tsconfig.app.json 적용을 받는데, 거기엔 브라우저 코드용으로
// "types": [...] 가 제한돼 있어 node 전역이 기본으로는 안 잡힌다. 파일 상단의
// 삼중 슬래시 참조로 이 파일에서만 명시적으로 node 타입을 끌어온다.
const css = readFileSync(join(process.cwd(), "src/styles/base.css"), "utf-8");

describe("reduced motion support (#189)", () => {
  it("globally disables animation/transition duration under prefers-reduced-motion: reduce", () => {
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(css).toMatch(/animation-duration:\s*0\.01ms\s*!important/);
    expect(css).toMatch(/transition-duration:\s*0\.01ms\s*!important/);
  });
});
