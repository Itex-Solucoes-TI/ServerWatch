/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#E6F7FA',
          100: '#B3E8F0',
          200: '#80D9E6',
          300: '#59D5C6',
          400: '#4FC4C2',
          500: '#1A8EAE',
          600: '#1886AD',
          700: '#136E8C',
          800: '#001145',
          900: '#06080D',
        }
      }
    },
  },
  plugins: [],
}
