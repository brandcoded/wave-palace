"use client";

import { usePathname } from "next/navigation";
import { Disc3 } from "lucide-react";

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
          className="group flex items-center gap-2 font-semibold tracking-tight text-wp-white"
          aria-label="WavePalace home"
        >
          <Disc3 className="h-6 w-6 text-wave-400 transition-transform group-hover:rotate-90" />
          <span className="text-base">Wave<span className="text-gradient">Palace</span></span>
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
          className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10"
        >
          Browse channels
        </a>
      </div>
    </header>
  );
}
