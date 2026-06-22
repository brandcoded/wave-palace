import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070512",
          900: "#0c0a1f",
          800: "#141133",
        },
        wave: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
        glow: {
          cyan: "#38e8ff",
          magenta: "#ff5cc8",
          amber: "#ffb347",
        },
        "wp-black": "#0D0B14",
        "wp-s1": "#161320",
        "wp-s2": "#1E1A2E",
        "wp-violet": "#7C3AED",
        "wp-violet2": "#4B2D8C",
        "wp-amber": "#D97706",
        "wp-white": "#F8F7FF",
        "wp-muted": "#9B8EC4",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
        drift: {
          "0%, 100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(0,-3%,0) scale(1.08)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s ease-out both",
        "pulse-soft": "pulse-soft 3s ease-in-out infinite",
        drift: "drift 18s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
