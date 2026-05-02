/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0a1628",
        ink: "#172033",
        cream: "#f5f0e8",
        paper: "#fffaf1",
        gold: "#c9a84c",
        forest: "#2d6a4f",
        rust: "#b64b3c",
      },
      fontFamily: {
        serif: ['"Playfair Display"', "Georgia", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
      boxShadow: {
        newspaper: "0 4px 24px rgba(10,22,40,0.12)",
      },
    },
  },
  plugins: [],
};
