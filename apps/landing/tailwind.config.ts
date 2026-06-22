import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "wp-black":   "#0D0B14",
        "wp-s1":      "#161320",
        "wp-s2":      "#1E1A2E",
        "wp-violet":  "#7C3AED",
        "wp-violet2": "#4B2D8C",
        "wp-amber":   "#D97706",
        "wp-white":   "#F8F7FF",
        "wp-muted":   "#9B8EC4",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
