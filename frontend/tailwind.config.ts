import type { Config } from "tailwindcss"

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base:   "#060C1A",
        sunken: "#04070F",
        raised: "#0A1326",
        cyan:   { DEFAULT: "#38E1FF" },
        azure:  "#4D8DFF",
        indigo: "#6E8BFF",
        ink: {
          primary:   "#EAF2FF",
          secondary: "#9DB2D4",
          tertiary:  "#5C708F",
        },
        data: {
          feature:  "#2FD4A7",
          refactor: "#6E8BFF",
          bugfix:   "#FF6E8A",
          test:     "#38E1FF",
          arch:     "#B98CFF",
        },
        success: "#2FD4A7",
        warning: "#FFC56E",
        danger:  "#FF6E8A",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        sans:    ["Inter", "sans-serif"],
        mono:    ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        sm:   "8px",
        md:   "14px",
        lg:   "20px",
        xl:   "28px",
        pill: "999px",
      },
      boxShadow: {
        panel: "0 20px 60px -20px rgba(2,6,18,.8)",
        glow:  "0 0 40px -8px rgba(56,225,255,.35)",
      },
      backdropBlur: {
        glass: "18px",
      },
    },
  },
  plugins: [],
} satisfies Config
