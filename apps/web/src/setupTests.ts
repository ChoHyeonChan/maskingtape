import "@testing-library/jest-dom/vitest";

// jsdom은 matchMedia를 구현하지 않는다 — prefers-reduced-motion 등을 확인하는 코드가
// 테스트에서 "matchMedia is not a function"으로 죽지 않도록 항상 false(매치 안 됨)를
// 반환하는 최소 스텁을 전역에 둔다.
if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// jsdom은 scrollIntoView도 구현하지 않는다 — 개별 테스트가 필요하면 자체 vi.fn()으로
// 덮어써서 호출 여부를 검증하고, 그 외 테스트는 이 기본 스텁으로 에러 없이 지나간다.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
