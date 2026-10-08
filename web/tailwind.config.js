/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#090a0f',
          900: '#0e1117',
          850: '#131722',
          800: '#1a1f2c',
          700: '#282f44',
          600: '#3a445e',
        }
      }
    },
  },
  plugins: [],
}
