/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // The palette the DOCX renderer already uses, so the console and the
        // deliverable do not look like two products.
        navy: '#1B2A4A',
        gold: '#B8960C',
        ink: '#3A3A3A',
        mist: '#E8F0FE',
      },
      fontFamily: {
        // Tabular figures matter: a rent roll that does not align is unreadable.
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
