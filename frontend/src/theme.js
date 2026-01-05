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

  // 15 Official Disaster Types + 2 Special (Refined for Premium Contrast)
  storm: "#2563eb",           // Blue 600
  flood: "#0ea5e9",           // Sky 500
  flash_flood: "#06b6d4",     // Cyan 500
  landslide: "#92400e",       // Amber 800
  subsidence: "#44403c",      // Stone 800
  drought: "#f97316",         // Orange 500
  salinity: "#0369a1",        // Sky 700
  extreme_weather: "#fbbf24", // Amber 400
  heatwave: "#ef4444",        // Red 500
  cold_surge: "#6366f1",      // Indigo 500
  earthquake: "#475569",      // Slate 600
  tsunami: "#1e3a8a",         // Blue 900
  storm_surge: "#8b5cf6",     // Violet 500
  wildfire: "#b91c1c",        // Red 700
  erosion: "#db2777",         // Pink 600
  
  warning_forecast: "#fde047", // Yellow 300
  recovery: "#10b981",         // Emerald 500
  
  unknown: "#94a3b8",          // Slate 400
};

export const DISASTER_METADATA = {
    storm: { label: "Bão, ATNĐ", tone: "blue", color: THEME_COLORS.storm },
    flood: { label: "Lũ lụt", tone: "sky", color: THEME_COLORS.flood },
    flash_flood: { label: "Lũ quét, Lũ ống", tone: "cyan", color: THEME_COLORS.flash_flood },
    landslide: { label: "Sạt lở", tone: "amber", color: THEME_COLORS.landslide },
    subsidence: { label: "Sụt lún đất", tone: "slate", color: THEME_COLORS.subsidence },
    drought: { label: "Hạn hán", tone: "orange", color: THEME_COLORS.drought },
    salinity: { label: "Xâm nhập mặn", tone: "indigo", color: THEME_COLORS.salinity },
    extreme_weather: { label: "Mưa lớn, Lốc, Sét, Mưa Đá", tone: "amber", color: THEME_COLORS.extreme_weather },
    heatwave: { label: "Nắng nóng", tone: "red", color: THEME_COLORS.heatwave },
    cold_surge: { label: "Rét hại, Sương muối", tone: "indigo", color: THEME_COLORS.cold_surge },
    earthquake: { label: "Động đất", tone: "slate", color: THEME_COLORS.earthquake },
    tsunami: { label: "Sóng thần", tone: "blue", color: THEME_COLORS.tsunami },
    storm_surge: { label: "Nước dâng", tone: "violet", color: THEME_COLORS.storm_surge },
    wildfire: { label: "Cháy rừng", tone: "rose", color: THEME_COLORS.wildfire },
    erosion: { label: "Xói lở", tone: "pink", color: THEME_COLORS.erosion },
    warning_forecast: { label: "Cảnh báo, dự báo", tone: "yellow", color: THEME_COLORS.warning_forecast },
    recovery: { label: "Khắc phục hậu quả", tone: "emerald", color: THEME_COLORS.recovery },
    unknown: { label: "Chưa phân loại", tone: "slate", color: THEME_COLORS.unknown },
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

