/** @type {import('tailwindcss').Config} */
module.exports = {
  // Paths are relative to this config's directory (/build/web) in the builder stage.
  content: ["../app/**/*.{html,js}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
