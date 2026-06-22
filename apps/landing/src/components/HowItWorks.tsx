"use client";

import { motion, useReducedMotion } from "framer-motion";
import { steps } from "@/lib/data";

export function HowItWorks() {
  const shouldReduce = useReducedMotion();

  return (
    <section
      id="how-it-works"
      className="border-t py-20"
      style={{ borderColor: "var(--wp-border)" }}
      aria-labelledby="how-heading"
    >
      <div className="mx-auto max-w-6xl px-6">
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.15em] text-wp-violet">
          How it works
        </p>
        <h2
          id="how-heading"
          className="mb-16 max-w-sm text-2xl font-light tracking-tight text-wp-white"
        >
          Four steps from files to dial.
        </h2>

        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: shouldReduce ? 0 : 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: i * 0.1, duration: 0.5, ease: "easeOut" }}
            >
              <p className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-wp-violet">
                {step.label}
              </p>
              <p className="mb-2 text-lg font-light leading-snug tracking-tight text-wp-white">
                {step.headline}
              </p>
              <p className="text-sm leading-relaxed text-wp-muted">
                {step.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
