"use client";

import { motion, useReducedMotion } from "framer-motion";
import { listenerPersonas } from "@/lib/data";

export function ListenerPersonas() {
  const shouldReduce = useReducedMotion();

  return (
    <section
      className="border-t py-20"
      style={{ borderColor: "var(--wp-border)" }}
      aria-labelledby="listener-personas-heading"
    >
      <div className="mx-auto max-w-6xl px-6">
        <h2
          id="listener-personas-heading"
          className="mb-16 max-w-[460px] text-2xl font-light leading-snug tracking-tight text-wp-white"
        >
          There&apos;s a channel for wherever you are right now.
        </h2>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {listenerPersonas.map((p, i) => (
            <motion.article
              key={p.tag}
              className="flex flex-col rounded-md border"
              style={{
                backgroundColor: "var(--wp-s1)",
                borderColor: "var(--wp-border)",
              }}
              initial={{ opacity: 0, y: shouldReduce ? 0 : 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: i * 0.1, duration: 0.5, ease: "easeOut" }}
            >
              <div className="flex flex-1 flex-col p-6">
                <p className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-wp-violet">
                  {p.tag}
                </p>
                <p className="mb-3 text-base font-medium text-wp-white">
                  {p.title}
                </p>
                <p className="flex-1 text-sm leading-relaxed text-wp-muted">
                  {p.body}
                </p>
              </div>
              <div
                className="border-t px-6 py-4"
                style={{ borderColor: "var(--wp-border)" }}
              >
                <p className="text-sm italic text-wp-white">{p.pitch}</p>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
