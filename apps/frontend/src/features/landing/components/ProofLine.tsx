"use client";

import { motion, useReducedMotion } from "framer-motion";

export function ProofLine() {
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
          &ldquo;Think of it as your music in a venue that&apos;s{" "}
          <span className="text-wp-violet">always open.</span>&rdquo;
        </motion.p>

        <motion.div
          className="mt-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <a
            href="/submit"
            className="rounded border border-wp-violet bg-wp-violet px-6 py-2.5 text-sm font-medium text-white transition hover:bg-wp-violet2"
          >
            Start your channel
          </a>
        </motion.div>
      </div>
    </section>
  );
}
