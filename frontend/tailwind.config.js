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
          DEFAULT: '#1F4AFF', // Sanad Blue
          dark: '#172FCC',
        },
        success: '#27C28B',
        warning: '#FFB020',
        error: '#FF4D4F',
        surface: '#F9FAFB',
        gray: {
          50: '#F9FAFB',
          100: '#F2F3F5',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827'
        }
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      }
    },
  },
  plugins: [],
} 