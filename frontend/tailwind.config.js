/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          base: '#0f1419',
          raised: '#1a2332',
          header: '#151c28',
        },
        border: {
          default: '#334155',
        },
        text: {
          primary: '#f1f5f9',
          secondary: '#94a3b8',
        },
        accent: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
        },
        status: {
          idle: '#22d3ee',
          pickup: '#fbbf24',
          rider: '#34d399',
          reposition: '#a78bfa',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
