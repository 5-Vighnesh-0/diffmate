import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom lacks these browser APIs; motion and the landing page use them.
export function stubBrowser({ reduceMotion = false } = {}) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduceMotion && query.includes("reduce"),
    media: query,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
  }));
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
}
stubBrowser();

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  stubBrowser();
});
