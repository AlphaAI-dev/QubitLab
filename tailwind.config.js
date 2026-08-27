/** @type {import('tailwindcss').Config} */
// Every color/font here is a passthrough to the CSS custom properties in
// index.css — that file is the brand's source of truth, this one just makes
// the tokens available to Tailwind's utility classes.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--ql-border))",
        background: "hsl(var(--ql-bg))",
        foreground: "hsl(var(--ql-text))",
        ql: {
          bg: "hsl(var(--ql-bg))",
          "bg-soft": "hsl(var(--ql-bg-soft))",
          surface: "hsl(var(--ql-surface))",
          "surface-2": "hsl(var(--ql-surface-2))",
          border: "hsl(var(--ql-border))",
          "border-hi": "hsl(var(--ql-border-hi))",
          text: "hsl(var(--ql-text))",
          "text-dim": "hsl(var(--ql-text-dim))",
          "text-faint": "hsl(var(--ql-text-faint))",
          zero: "hsl(var(--ql-zero))",
          one: "hsl(var(--ql-one))",
          xp: "hsl(var(--ql-xp))",
          miss: "hsl(var(--ql-miss))",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Instrument Serif", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SF Mono", "Menlo", "monospace"],
      },
      backgroundImage: {
        superposition: "linear-gradient(96deg, hsl(var(--ql-zero)), hsl(var(--ql-one)))",
      },
    },
  },
  plugins: [],
};
