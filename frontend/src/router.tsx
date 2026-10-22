import { useEffect, useState, type AnchorHTMLAttributes, type MouseEvent } from "react";

const EVENT = "app:navigate";

export function navigate(to: string, { replace = false } = {}) {
  if (to === window.location.pathname + window.location.search) return;
  window.history[replace ? "replaceState" : "pushState"](null, "", to);
  window.dispatchEvent(new Event(EVENT));
  window.scrollTo({ top: 0 });
}

export function usePath(): string {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    window.addEventListener("popstate", update);
    window.addEventListener(EVENT, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(EVENT, update);
    };
  }, []);
  return path;
}

/** Match "/app/posts/:id" style patterns; returns params or null. */
export function match(pattern: string, path: string): Record<string, string> | null {
  const a = pattern.split("/").filter(Boolean);
  const b = path.split("/").filter(Boolean);
  if (a.length !== b.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < a.length; i++) {
    if (a[i].startsWith(":")) params[a[i].slice(1)] = decodeURIComponent(b[i]);
    else if (a[i] !== b[i]) return null;
  }
  return params;
}

export function Link({ to, onClick, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { to: string }) {
  function handle(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event);
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    navigate(to);
  }
  return <a href={to} onClick={handle} {...rest} />;
}
