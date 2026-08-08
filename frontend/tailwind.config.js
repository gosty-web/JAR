/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'orb-idle': 'orbIdle 4s ease-in-out infinite',
        'orb-listen': 'orbListen 2s ease-in-out infinite',
        'orb-work': 'orbWork 1.5s ease-in-out infinite',
      },
      keyframes: {
        orbIdle: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.8' },
          '50%': { transform: 'scale(1.05)', opacity: '1' },
        },
        orbListen: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.9', boxShadow: '0 0 20px rgba(59, 130, 246, 0.5)' },
          '50%': { transform: 'scale(1.15)', opacity: '1', boxShadow: '0 0 40px rgba(59, 130, 246, 0.8)' },
        },
        orbWork: {
          '0%': { transform: 'rotate(0deg) scale(1.1)' },
          '100%': { transform: 'rotate(360deg) scale(1.1)' },
        }
      }
    },
  },
  plugins: [],
}
