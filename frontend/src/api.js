export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function getJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export function fmtType(t) {
  const map = {
    // Decision 18/2021/QD-TTg Exact Names
    storm: "Bão và áp thấp nhiệt đới",
    flood_landslide: "Mưa lớn và lũ lụt",
    heat_drought: "Nắng nóng, hạn hán, xâm nhập mặn",
    wind_fog: "Gió mạnh, sương mù",
    storm_surge: "Nước dâng",
    extreme_other: "Các hiện tượng thời tiết cực đoan khác",
    wildfire: "Cháy rừng tự nhiên",
    quake_tsunami: "Động đất và sóng thần",
    
    // Legacy mapping (normalize to new names)
    flood: "Mưa lớn và lũ lụt",
    landslide: "Mưa lớn và lũ lụt",
    heavy_rain: "Mưa lớn và lũ lụt",
    earthquake: "Động đất và sóng thần",
    tsunami: "Động đất và sóng thần",
    wind_hail: "Các hiện tượng thời tiết cực đoan khác", 
    extreme_weather: "Nắng nóng, hạn hán, xâm nhập mặn",
    
    unknown: "Chưa phân loại",
  };
  return map[t] || t;
}

export function fmtVndBillion(x) {
  if (x === null || x === undefined) return "—";
  return `${x.toLocaleString("vi-VN")} tỷ`;
}

export function fmtDate(s) {
  const d = new Date(s);
  return d.toLocaleString("vi-VN");
}

export function fmtTimeAgo(s) {
  const d = new Date(s);
  const now = new Date();
  const seconds = Math.floor((now - d) / 1000);

  if (seconds < 60) return "Vừa xong";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} ngày trước`;

  return fmtDate(s);
}
