"use client";

import { motion, useReducedMotion } from "framer-motion";

export function ListenerProofLine() {
  const shouldReduce = useReducedMotion();

  return (
    <section
      className="border-t py-24 text-center"
      style={{ borderColor: "var(--wp-border)" }}
    >
      <div className="mx-auto max-w-4xl px-6">
        <motion.p
          className="text-3xl font-light leading-snug tracking-tight text-wp-white sm:text-4xl"
          initial={{ opacity: 0, y: shouldReduce ? 0 : 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          "Open it once.{" "}
          <span className="text-wp-violet">It&apos;s still on when you get back.</span>"
        </motion.p>

        <motion.div
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <a
            href="https://wavepalace.live"
            className="rounded border border-wp-violet bg-wp-violet px-6 py-2.5 text-sm font-medium text-white transition hover:bg-wp-violet2"
          >
            Browse channels
          </a>
          <a
            href="/"
            className="rounded border px-6 py-2.5 text-sm font-medium text-wp-muted transition hover:border-wp-violet hover:text-wp-white"
            style={{ borderColor: "var(--wp-border)" }}
          >
            For creators →
          </a>
        </motion.div>
      </div>
    </section>
  );
}
