/**
 * Centralized Design System Tokens
 * Shared across React Components (Recharts) and Tailwind Config
 */

export const THEME_COLORS = {
  // Brand / UI - Standardized Teal Brand
  brand: "#2fa1b3",
  brandLight: "#eef9fa",
  brandDark: "#258a9b",
  primary: "#2fa1b3", 
  secondary: "#64748b", // Slate 500
  
  // Neutral Semantic
  success: "#10b981", // Emerald 500
  warning: "#f59e0b", // Amber 500
  danger: "#ef4444",  // Red 500
  info: "#3b82f6",    // Blue 500

  // 14 Official Disaster Types + 2 Special (Refined for Premium Contrast)
  storm: "#2563eb",           // Blue 600
  flood: "#06b6d4",           // Cyan 500
  flash_flood: "#0d9488",     // Teal 600
  landslide: "#d97706",       // Amber 600
  subsidence: "#7c2d12",      // Brown 900
  drought: "#ea580c",         // Orange 600
  salinity: "#0284c7",        // Sky 600
  extreme_weather: "#ca8a04", // Yellow 600
  heatwave: "#dc2626",        // Red 600
  cold_surge: "#4f46e5",      // Indigo 600
  earthquake: "#4b5563",      // Slate 600
  tsunami: "#1e3a8a",         // Blue 900
  storm_surge: "#7c3aed",     // Violet 600
  wildfire: "#991b1b",        // Red 800
  
  warning_forecast: "#eab308", // Yellow 500
  recovery: "#059669",         // Emerald 600
  
  unknown: "#94a3b8",          // Slate 400
};

export const CHART_COLORS = [
  THEME_COLORS.storm,
  THEME_COLORS.flood,
  THEME_COLORS.flash_flood,
  THEME_COLORS.landslide,
  THEME_COLORS.drought,
  THEME_COLORS.extreme_weather,
  THEME_COLORS.heatwave,
  THEME_COLORS.wildfire,
];
