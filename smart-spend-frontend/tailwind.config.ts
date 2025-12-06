// smart-spend-frontend/tailwind.config.ts
import type { Config } from 'tailwindcss';

export default {
  // CRITICAL: Enables dark mode based on the 'dark' class on the HTML tag
  darkMode: 'class',
  content: [
    "./index.html",
    // Scan all component files in the src directory
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Defined colors from your design document
        'accent-primary': '#FFC720',
        'bg-dark': '#121212',
        'bg-light': '#F8F8F8',
        'text-dark': '#FFFFFF',
        'text-light': '#121212',
        'status-success': '#43A047',
        'status-fail': '#E53935',
        'status-info': '#00C2A0',
      },
    },
  },
  plugins: [],
} satisfies Config;