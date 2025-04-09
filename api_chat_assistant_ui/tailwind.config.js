/** @type {import('tailwindcss').Config} */
module.exports = { // Use module.exports for Tailwind v3
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}", // Scan source files for classes
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  }
  