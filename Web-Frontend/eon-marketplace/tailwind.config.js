/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        deepblack: "#050505",
        accent: "#FFB238",
        goldlight: "#FFC95C",
        white: "#FFFFFF",
        softgray: "#ECECEC",
      },
      boxShadow: {
        glow: "0 0 20px rgba(255, 178, 56, 0.4)",
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
