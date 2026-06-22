"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "https://api.wavepalace.live");

interface LiveChannel {
  slug: string;
  title: string;
  genre: string[];
  playCount: number;
  isPublished: boolean;
}

const WAVEFORM_HEIGHTS = [
  40, 65, 30, 80, 55, 70, 35, 90, 50, 75,
  45, 85, 38, 60, 78, 42, 68, 52, 82, 48,
];

const SKELETON_COUNT = 4;

export function PlayerMock() {
  const shouldReduce = useReducedMotion();
  const [channels, setChannels] = useState<LiveChannel[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/channels`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: LiveChannel[]) => {
        const published = data.filter((c) => c.isPublished);
        setChannels(published.slice(0, 4));
      })
      .catch(() => {
        /* silently keep null — skeletons stay */
      });
    return () => controller.abort();
  }, []);

  const featured = channels?.[0];

  const cardVariant = {
    hidden: { opacity: 0, y: shouldReduce ? 0 : 24 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
  };

  const sidebarItem = (i: number) => ({
    hidden: { opacity: 0, x: shouldReduce ? 0 : 16 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { delay: 0.3 + i * 0.08, duration: 0.4, ease: "easeOut" },
    },
  });

  return (
    <section
      id="player"
      className="py-20"
      aria-labelledby="player-section-heading"
    >
      <div className="mx-auto max-w-6xl px-6">
        <p
          id="player-section-heading"
          className="mb-12 text-center text-xs font-medium uppercase tracking-[0.15em] text-wp-muted"
        >
          What it looks like
        </p>

        <div className="flex flex-col gap-6 lg:flex-row">
          <motion.div
            className="flex-1 rounded-md border"
            style={{
              backgroundColor: "var(--wp-s1)",
              borderColor: "var(--wp-border)",
            }}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            variants={cardVariant}
          >
            <div
              className="relative flex h-40 items-center justify-center overflow-hidden rounded-t-md"
              style={{ backgroundColor: "var(--wp-s2)" }}
            >
              <div
                aria-hidden="true"
                className="absolute inset-0 opacity-[0.15]"
                style={{
                  backgroundImage:
                    "repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(124,58,237,0.4) 24px), repeating-linear-gradient(90deg, transparent, transparent 23px, rgba(124,58,237,0.4) 24px)",
                }}
              />
              <svg
                aria-hidden="true"
                className="absolute inset-0 h-full w-full opacity-30"
                viewBox="0 0 400 160"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle cx="200" cy="160" r="100" stroke="var(--wp-violet)" strokeWidth="1" />
                <circle cx="200" cy="160" r="140" stroke="var(--wp-violet)" strokeWidth="0.75" strokeDasharray="4 6" />
              </svg>
              <svg
                aria-label="Play"
                className="relative z-10"
                width="44"
                height="44"
                viewBox="0 0 44 44"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle cx="22" cy="22" r="21" stroke="var(--wp-violet)" strokeWidth="1" />
                <path d="M18 15l12 7-12 7V15z" fill="var(--wp-violet)" />
              </svg>
            </div>

            <div className="px-5 pt-4">
              {featured ? (
                <>
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-wp-muted">
                    {featured.title}
                  </p>
                  <p className="mt-1 text-base font-medium text-wp-white">
                    {featured.genre[0] ?? "Music"}
                  </p>
                  <p className="text-sm text-wp-muted">
                    {featured.playCount.toLocaleString()} plays
                  </p>
                </>
              ) : (
                <div className="space-y-2">
                  <div className="h-3 w-24 animate-pulse rounded" style={{ backgroundColor: "var(--wp-s2)" }} />
                  <div className="h-4 w-36 animate-pulse rounded" style={{ backgroundColor: "var(--wp-s2)" }} />
                  <div className="h-3 w-20 animate-pulse rounded" style={{ backgroundColor: "var(--wp-s2)" }} />
                </div>
              )}
            </div>

            <div
              className="mx-5 mt-4 flex items-end gap-[2px]"
              role="img"
              aria-label="audio waveform"
            >
              {WAVEFORM_HEIGHTS.map((h, i) => (
                <span
                  key={i}
                  className="w-1 flex-1 rounded-sm"
                  style={{
                    height: `${h * 0.3}px`,
                    backgroundColor: "var(--wp-violet)",
                    opacity: i < 7 ? 0.9 : 0.45,
                  }}
                />
              ))}
            </div>

            <div
              className="mx-5 mt-2 h-[2px] rounded-sm"
              style={{ backgroundColor: "var(--wp-s2)" }}
            >
              <div
                className="h-full rounded-sm"
                style={{ width: "38%", backgroundColor: "var(--wp-violet)" }}
              />
            </div>

            <div className="flex items-center justify-between px-5 py-4">
              <span className="text-xs text-wp-muted">Live</span>
              <span
                className="rounded px-2 py-0.5 text-xs font-medium"
                style={{
                  color: "var(--wp-amber)",
                  backgroundColor: "rgba(217,119,6,0.15)",
                  border: "1px solid rgba(217,119,6,0.3)",
                }}
              >
                ● On Air
              </span>
            </div>
          </motion.div>

          <div
            className="w-full rounded-md border lg:w-72"
            style={{
              backgroundColor: "var(--wp-s1)",
              borderColor: "var(--wp-border)",
            }}
          >
            <div
              className="border-b px-5 py-4"
              style={{ borderColor: "var(--wp-border)" }}
            >
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-wp-muted">
                Active channels
              </p>
            </div>

            <ul className="divide-y" style={{ borderColor: "var(--wp-border)" }}>
              {channels
                ? channels.map((ch, i) => (
                    <motion.li
                      key={ch.slug}
                      className="flex items-center justify-between px-5 py-3"
                      initial="hidden"
                      whileInView="visible"
                      viewport={{ once: true }}
                      variants={sidebarItem(i)}
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="h-2 w-2 rounded-sm"
                          style={{
                            backgroundColor:
                              i === 0 ? "var(--wp-amber)" : "var(--wp-violet)",
                          }}
                          aria-hidden="true"
                        />
                        <div>
                          <p className="text-sm font-medium text-wp-white">{ch.title}</p>
                          <p className="text-xs text-wp-muted">{ch.genre[0] ?? "Music"}</p>
                        </div>
                      </div>
                      <span className="text-xs text-wp-muted">
                        {ch.playCount.toLocaleString()} ▶
                      </span>
                    </motion.li>
                  ))
                : Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                    <li key={i} className="flex items-center gap-3 px-5 py-3">
                      <span
                        className="h-2 w-2 animate-pulse rounded-sm"
                        style={{ backgroundColor: "var(--wp-s2)" }}
                      />
                      <div className="flex-1 space-y-1">
                        <div className="h-3 w-28 animate-pulse rounded" style={{ backgroundColor: "var(--wp-s2)" }} />
                        <div className="h-2.5 w-16 animate-pulse rounded" style={{ backgroundColor: "var(--wp-s2)" }} />
                      </div>
                    </li>
                  ))}
            </ul>

            <div
              className="m-4 rounded border p-4"
              style={{
                backgroundColor: "var(--wp-s2)",
                borderColor: "var(--wp-border)",
              }}
            >
              <p className="text-xs leading-relaxed text-wp-muted">
                One popular VRChat world. Your name on the dial. No one has to look you up.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
