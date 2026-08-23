/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Four voices — see index.html
        display: ['"Clash Display"', 'system-ui', 'sans-serif'],
        sans: ['"General Sans"', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],       // the spoken word
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: '#0B1F17',                                                 // deep forest-black — text + sidebar
        palm: { DEFAULT: '#0B6E4F', dark: '#08533C', light: '#E7F4EF' },// brand / infrastructure
        mint: { DEFAULT: '#2FD8A6', soft: '#DAF7EC' },                  // live voice / accent
        iris: { DEFAULT: '#4338CA', light: '#ECEBFB' },                 // legal / justice
        gold: { DEFAULT: '#B98829', deep: '#8A6414', light: '#F7EFDD' },// mother tongue / "we'd rather ask"
        paper: '#F3F6F4',                                               // app background
        surface: '#FFFFFF',                                             // cards
        warm: '#FBF8F1',                                                // the human / voice zones
        line: '#E4EAE7',                                                // hairline borders
        muted: '#5B6B63',                                               // secondary text (green-grey)

        // keep the old brand.* names alive so no stray class silently breaks
        brand: {
          dark: '#0B1F17', sidebar: '#0B1F17', primary: '#0B6E4F',
          primaryHover: '#08533C', accent: '#2FD8A6', accentLight: '#DAF7EC',
          bg: '#F3F6F4', surface: '#FFFFFF', border: '#E4EAE7', muted: '#5B6B63',
        },
      },
      fontSize: {
        thesis: ['clamp(2.4rem, 4.6vw, 3.5rem)', { lineHeight: '1.0', letterSpacing: '-0.035em' }],
        hero:   ['clamp(1.8rem, 3.2vw, 2.5rem)', { lineHeight: '1.05', letterSpacing: '-0.025em' }],
      },
      boxShadow: {
        card: '0 1px 2px rgba(11,31,23,0.04), 0 10px 28px -16px rgba(11,31,23,0.14)',
        lift: '0 18px 48px -20px rgba(11,31,23,0.28)',
      },
      borderRadius: {
        xl2: '1.375rem',
      },
      keyframes: {
        settle:   { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        wordreveal: { '0%': { opacity: '0', filter: 'blur(3px)', transform: 'translateY(2px)' }, '100%': { opacity: '1', filter: 'blur(0)', transform: 'translateY(0)' } },
        equalize: { '0%,100%': { transform: 'scaleY(0.32)' }, '50%': { transform: 'scaleY(1)' } },
        breathe:  { '0%,100%': { transform: 'scale(1)', opacity: '0.45' }, '50%': { transform: 'scale(1.08)', opacity: '0.75' } },
        drawin:   { '0%': { transform: 'scaleY(0.15)', opacity: '0' }, '100%': { transform: 'scaleY(1)', opacity: '1' } },
      },
      animation: {
        settle: 'settle 0.6s cubic-bezier(0.22,1,0.36,1) both',
        wordreveal: 'wordreveal 0.45s ease both',
        equalize: 'equalize 0.9s ease-in-out infinite',
        breathe: 'breathe 3.2s ease-in-out infinite',
        drawin: 'drawin 0.5s cubic-bezier(0.22,1,0.36,1) both',
      },
    },
  },
  plugins: [],
}
