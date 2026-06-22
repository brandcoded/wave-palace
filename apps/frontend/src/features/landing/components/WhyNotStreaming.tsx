"use client";

import { motion, useReducedMotion } from "framer-motion";

const comparisons = [
  {
    theirs: "Algorithmic playlists",
    ours: "Human-curated channels",
    detail: "Every channel is someone's genuine taste, not a model's guess.",
  },
  {
    theirs: "Interrupting ads",
    ours: "No ads, no interruptions",
    detail: "The music plays. That's the whole product.",
  },
  {
    theirs: "Skipping, fiddling, managing",
    ours: "Open it and leave it on",
    detail: "A channel loops continuously. You don't have to babysit it.",
  },
  {
    theirs: "Locked behind accounts",
    ours: "No account required",
    detail: "A URL is all you need. Open it in any browser, anywhere.",
  },
];

export function WhyNotStreaming() {
  const shouldReduce = useReducedMotion();

  return (
    <section
      className="border-t py-20"
      style={{ borderColor: "var(--wp-border)" }}
      aria-labelledby="why-heading"
    >
      <div className="mx-auto max-w-6xl px-6">
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.15em] text-wp-violet">
          Different by design
        </p>
        <h2
          id="why-heading"
          className="mb-16 max-w-lg text-2xl font-light tracking-tight text-wp-white"
        >
          Not a playlist. Not a streaming service. A radio station that&apos;s
          always on.
        </h2>

        <div className="grid gap-4 sm:grid-cols-2">
          {comparisons.map((item, i) => (
            <motion.div
              key={i}
              className="rounded-md border p-6"
              style={{
                backgroundColor: "var(--wp-s1)",
                borderColor: "var(--wp-border)",
              }}
              initial={{ opacity: 0, y: shouldReduce ? 0 : 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: i * 0.08, duration: 0.45, ease: "easeOut" }}
            >
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <span
                  className="rounded px-2 py-0.5 text-xs text-wp-muted line-through"
                  style={{ backgroundColor: "var(--wp-s2)" }}
                >
                  {item.theirs}
                </span>
                <span className="text-wp-muted">→</span>
                <span
                  className="rounded px-2 py-0.5 text-xs font-medium text-wp-violet"
                  style={{ backgroundColor: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.25)" }}
                >
                  {item.ours}
                </span>
              </div>
              <p className="text-sm leading-relaxed text-wp-muted">{item.detail}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
