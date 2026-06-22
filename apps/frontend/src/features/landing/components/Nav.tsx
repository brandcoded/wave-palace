"use client";

import { usePathname } from "next/navigation";

export function LandingNav() {
  const pathname = usePathname();

  return (
    <header
      className="sticky top-0 z-50 border-b bg-wp-black/80 backdrop-blur-sm"
      style={{ borderColor: "var(--wp-border)" }}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a
          href="/"
          className="text-base font-semibold tracking-tight text-wp-white"
          aria-label="WavePalace home"
        >
          Wave<span className="text-wp-violet">Palace</span>
        </a>

        <nav className="hidden items-center gap-8 sm:flex" aria-label="Site navigation">
          <a
            href="/creators"
            className={`text-sm transition ${pathname === "/creators" ? "text-wp-white" : "text-wp-muted hover:text-wp-white"}`}
          >
            For creators
          </a>
          <a
            href="/listeners"
            className={`text-sm transition ${pathname === "/listeners" ? "text-wp-white" : "text-wp-muted hover:text-wp-white"}`}
          >
            For listeners
          </a>
        </nav>

        <a
          href="/"
          className="rounded border border-wp-violet bg-wp-violet px-4 py-1.5 text-sm font-medium text-white transition hover:bg-wp-violet2"
        >
          Browse channels
        </a>
      </div>
    </header>
  );
}
