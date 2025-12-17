export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function getJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export function fmtType(t) {
  const map = {
    storm: "Bão/ATNĐ",
    flood: "Mưa lũ/Ngập",
    landslide: "Sạt lở/Lũ quét",
    earthquake: "Động đất",
    tsunami: "Sóng thần",
    wind_hail: "Gió mạnh/Dông lốc",
    wildfire: "Cháy rừng",
    extreme_weather: "Khí hậu cực đoan",
    unknown: "Khác",
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
