/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        soft: '0 10px 30px rgba(2, 6, 23, 0.08)',
        card: '0 18px 40px rgba(2, 6, 23, 0.10)',
      },
    },
  },
  plugins: [],
}

