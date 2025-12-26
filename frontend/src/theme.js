/**
 * Centralized Design System Tokens
 * Shared across React Components (Recharts) and Tailwind Config
 */

export const THEME_COLORS = {
  // Brand / UI
  primary: "#0f172a", // Slate 900
  secondary: "#334155", // Slate 700
  background: "#f8fafc", // Slate 50
  surface: "#ffffff",
  border: "#e2e8f0", // Slate 200

  // 14 Official Disaster Types
  storm: "#3B82F6",           // Blue 500
  flood: "#06B6D4",           // Cyan 500
  flash_flood: "#14B8A6",     // Teal 500
  landslide: "#F59E0B",       // Amber 500
  subsidence: "#78350F",      // Brown 900 -> used 78350F for better contrast
  drought: "#F97316",         // Orange 500
  salinity: "#0EA5E9",        // Sky 500
  extreme_weather: "#EAB308", // Yellow 500
  heatwave: "#EF4444",        // Red 500
  cold_surge: "#6366F1",      // Indigo 500
  earthquake: "#475569",      // Slate 600
  tsunami: "#1E3A8A",         // Blue 900
  storm_surge: "#8B5CF6",     // Violet 500
  wildfire: "#B91C1C",        // Red 700

  // 2 Special Groups
  warning_forecast: "#FACC15", // Yellow 400
  recovery: "#10B981",         // Emerald 500
  
  unknown: "#94A3B8",          // Slate 400
};

export const CHART_COLORS = [
  THEME_COLORS.storm,
  THEME_COLORS.flood,
  THEME_COLORS.flash_flood,
  THEME_COLORS.landslide,
  THEME_COLORS.subsidence,
  THEME_COLORS.extreme_weather,
];
