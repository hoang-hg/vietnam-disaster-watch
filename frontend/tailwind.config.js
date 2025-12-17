/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'sans-serif'],
      },
      colors: {
        disaster: {
          storm: "#0284c7", // Sky 600
          flood: "#06b6d4", // Cyan 500
          landslide: "#b45309", // Amber 700
          earthquake: "#16a34a", // Green 600
          tsunami: "#7e22ce", // Purple 700
          wind_hail: "#0891b2", // Cyan 600
          wildfire: "#ea580c", // Orange 600
          extreme_weather: "#dc2626", // Red 600
          unknown: "#64748b", // Slate 500
        }
      }
    },
  },
  plugins: [],
}
