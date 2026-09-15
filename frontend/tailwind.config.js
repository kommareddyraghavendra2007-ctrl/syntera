/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        syntera: {
          50:  '#f0f4ff',
          100: '#dde6ff',
          200: '#c0cfff',
          300: '#94acff',
          400: '#607cff',
          500: '#3d56f5',
          600: '#2d3ee8',
          700: '#242fd4',
          800: '#2229ab',
          900: '#212787',
          950: '#161752',
        },
        surface: {
          DEFAULT: '#0f1117',
          secondary: '#161b25',
          tertiary:  '#1e2432',
          border:    '#2a3142',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
