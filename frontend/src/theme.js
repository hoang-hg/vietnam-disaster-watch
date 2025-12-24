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

  // Disaster Types (Vibrant & Harmoneous)
  storm: "#3B82F6", // Blue 500
  flood_landslide: "#06B6D4", // Cyan 500
  heat_drought: "#F97316", // Orange 500
  wind_fog: "#64748B", // Slate 500
  extreme_other: "#EAB308", // Yellow 500
  wildfire: "#EF4444", // Red 500
  quake_tsunami: "#10B981", // Emerald 500
  recovery: "#6366F1", // Indigo 500
  relief_aid: "#EC4899", // Pink 500
  
  unknown: "#94A3B8", // Slate 400
};

export const CHART_COLORS = [
  THEME_COLORS.storm,
  THEME_COLORS.flood_landslide,
  THEME_COLORS.heat_drought,
  THEME_COLORS.wind_fog,
  THEME_COLORS.storm_surge,
  THEME_COLORS.extreme_other,
];
