/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Clash Display"', '"Clash Grotesk"', 'sans-serif'],
        sans: ['"General Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        brand: {
          dark: '#0F172A',
          sidebar: '#0A1C16',
          primary: '#0B6E4F',
          primaryHover: '#08533C',
          accent: '#20C397',
          accentLight: '#E8F9F4',
          bg: '#F6FAFB',
          surface: '#FFFFFF',
          border: '#E6E7EA',
          muted: '#64748B',
        },
        civic: {
          green: '#22C55E',
          amber: '#F59E0B',
          indigo: '#6366F1',
          purple: '#8B5CF6',
          red: '#EF4444',
        }
      }
    },
  },
  plugins: [],
}
