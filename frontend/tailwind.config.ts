import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        bg:             "var(--color-bg)",
        surface:        "var(--color-surface)",
        "surface-2":    "var(--color-surface-2)",
        "surface-off":  "var(--color-surface-offset)",
        divider:        "var(--color-divider)",
        border:         "var(--color-border)",
        text:           "var(--color-text)",
        "text-muted":   "var(--color-text-muted)",
        "text-faint":   "var(--color-text-faint)",
        primary:        "var(--color-primary)",
        "primary-hover":"var(--color-primary-hover)",
        success:        "var(--color-success)",
        error:          "var(--color-error)",
        warning:        "var(--color-warning)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
    },
  },
  plugins: [],
};

export default config;
