import { type AnchorHTMLAttributes, type MouseEvent, useSyncExternalStore } from "react";

// Three routes do not need a router library: the History API plus a popstate event.
export function navigate(to: string) {
  history.pushState(null, "", to);
  dispatchEvent(new PopStateEvent("popstate"));
}

function subscribe(onChange: () => void) {
  addEventListener("popstate", onChange);
  return () => removeEventListener("popstate", onChange);
}

export function usePath() {
  return useSyncExternalStore(subscribe, () => location.pathname);
}

export function Link({ href, onClick, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  function handle(e: MouseEvent<HTMLAnchorElement>) {
    onClick?.(e);
    // Let the browser handle new tabs, downloads, and modified clicks.
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(href);
    scrollTo(0, 0);
  }
  return <a href={href} onClick={handle} {...rest} />;
}
