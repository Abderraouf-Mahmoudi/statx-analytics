/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#070B12",
        shell: "#0B0F19",
        sidebar: "#080D15",
        surface: "#111827",
        "surface-elevated": "#162033",
        border: "#263244",
        brand: "#4ADE80",
        action: "#10B981",
        info: "#22D3EE",
        warning: "#F59E0B",
        danger: "#EF4444"
      }
    }
  },
  plugins: []
};

