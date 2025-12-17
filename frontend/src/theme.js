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

  // Disaster Types (High Contrast & Distinct)
  // Disaster Types (High Contrast & Distinct)
  storm: "#0284c7", // Bão và áp thấp nhiệt đới
  flood_landslide: "#06b6d4", // Mưa lớn và lũ lụt
  heat_drought: "#fb923c", // Nắng nóng, hạn hán, xâm nhập mặn
  wind_fog: "#94a3b8", // Gió mạnh, sương mù
  storm_surge: "#7e22ce", // Nước dâng
  extreme_other: "#dc2626", // Các hiện tượng thời tiết cực đoan khác
  wildfire: "#ea580c", // Cháy rừng tự nhiên
  quake_tsunami: "#059669", // Động đất và sóng thần
  
  // Legacy Keys Support
  flood: "#06b6d4", 
  landslide: "#06b6d4",
  heavy_rain: "#06b6d4",
  earthquake: "#059669",
  tsunami: "#059669",
  wind_hail: "#dc2626",        
  extreme_weather: "#fb923c",  
  
  unknown: "#64748b", // Khác
};

export const CHART_COLORS = [
  THEME_COLORS.storm,
  THEME_COLORS.flood_landslide,
  THEME_COLORS.heat_drought,
  THEME_COLORS.wind_fog,
  THEME_COLORS.storm_surge,
  THEME_COLORS.extreme_other,
];
