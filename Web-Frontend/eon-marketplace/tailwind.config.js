/** @type {import('tailwindcss').Config} */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'], // <-- deine Font
      },
      colors: {
        space: "#1F2041",
        violet: "#4B3F72",
        sun: "#FFC857",
        cyan: "#119DA4",
        graypayne: "#19647E",
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'), // optional fancy content styles
  ],
}


