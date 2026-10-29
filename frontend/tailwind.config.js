/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        "pitch-dark": "#0B0F19",
        card: "#111827",
        "pitch-green": "#0F2D1A",
        "statx-green": "#10B981"
      },
      boxShadow: {
        card: "0 18px 45px rgba(0, 0, 0, 0.2)",
        glow: "0 0 24px rgba(16, 185, 129, 0.16)"
      }
    }
  },
  plugins: []
};

