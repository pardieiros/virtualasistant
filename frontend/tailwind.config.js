/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          gold: '#EAB308',
          'gold-soft': '#FACC15',
        },
        dark: {
          charcoal: '#111113',
          'warm-gray': '#27272A',
        },
        text: {
          light: '#F5F5F4',
          medium: '#D4D4D4',
        },
        status: {
          error: '#DC2626',
          success: '#65A30D',
        },
      },
    },
  },
  plugins: [],
}

