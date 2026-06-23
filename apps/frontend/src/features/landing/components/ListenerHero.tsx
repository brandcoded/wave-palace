"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";

const line1 = "No algorithm.".split(" ");
const line2 = "Just the dial.".split(" ");

export function ListenerHero() {
  const shouldReduce = useReducedMotion();

  const wordVariant: Variants = {
    hidden: { opacity: 0, y: shouldReduce ? 0 : 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.09, duration: 0.4, ease: "easeOut" },
    }),
  };

  const fadeIn: Variants = {
    hidden: { opacity: 0, y: shouldReduce ? 0 : 12 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: 0.45 + i * 0.1, duration: 0.5, ease: "easeOut" },
    }),
  };

  return (
    <section className="relative overflow-hidden pb-24 pt-20 sm:pb-32 sm:pt-28">
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 left-0 w-full opacity-[0.07]"
        viewBox="0 0 1200 120"
        preserveAspectRatio="none"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M0 60 Q100 20 200 60 Q300 100 400 60 Q500 20 600 60 Q700 100 800 60 Q900 20 1000 60 Q1100 100 1200 60"
          stroke="var(--wp-violet)"
          strokeWidth="1.5"
        />
        <path
          d="M0 80 Q150 40 300 80 Q450 120 600 80 Q750 40 900 80 Q1050 120 1200 80"
          stroke="var(--wp-violet)"
          strokeWidth="1"
        />
      </svg>

      <div className="relative mx-auto max-w-6xl px-6 text-center">
        <motion.p
          className="mb-6 text-xs font-medium uppercase tracking-[0.15em] text-wp-violet"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          For listeners
        </motion.p>

        <h1 className="mx-auto max-w-3xl text-4xl leading-tight tracking-tight sm:text-6xl lg:text-7xl">
          <span className="block font-light" style={{ color: "var(--wp-white)" }}>
            {line1.map((word, i) => (
              <motion.span
                key={i}
                className="inline-block"
                custom={i}
                initial="hidden"
                animate="visible"
                variants={wordVariant}
              >
                {word}&nbsp;
              </motion.span>
            ))}
          </span>
          <span className="block font-medium text-wp-violet">
            {line2.map((word, i) => (
              <motion.span
                key={i}
                className="inline-block"
                custom={line1.length + i}
                initial="hidden"
                animate="visible"
                variants={wordVariant}
              >
                {word}&nbsp;
              </motion.span>
            ))}
          </span>
        </h1>

        <motion.p
          className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-wp-muted sm:text-lg"
          custom={0}
          initial="hidden"
          animate="visible"
          variants={fadeIn}
        >
          Curated channels that play continuously — in your browser, in VRChat
          worlds, on any device. Open one and leave it on.
        </motion.p>

        <motion.div
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
          custom={1}
          initial="hidden"
          animate="visible"
          variants={fadeIn}
        >
          <a
            href="/"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-wave-500 to-glow-magenta px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-wave-600/30 transition hover:brightness-110"
          >
            Browse channels
          </a>
          <a
            href="#how-it-works"
            className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white/80 transition hover:bg-white/10"
          >
            How it works
          </a>
        </motion.div>
      </div>
    </section>
  );
}
