export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function getJson(path) {
  const token = localStorage.getItem("access_token");
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};
  const res = await fetch(API_BASE + path, { headers });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
    }
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

export async function deleteJson(path) {
  const token = localStorage.getItem("access_token");
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};
  const res = await fetch(API_BASE + path, { method: "DELETE", headers });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
    }
    let errorDetail = "";
    try {
        const errData = await res.json();
        errorDetail = errData.detail || "";
    } catch(e) {}
    
    throw new Error(errorDetail || `API error ${res.status}`);
  }
  return true;
}

export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });
  if (!res.ok) throw new Error("Sai email hoặc mật khẩu");
  return res.json();
}

export async function register(email, password, fullName) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || "Đăng ký thất bại");
  }
  return res.json();
}

export function fmtType(t) {
  const map = {
    // Decision 18/2021/QD-TTg Exact Names
    storm: "Bão, Áp thấp nhiệt đới",
    flood_landslide: "Mưa lớn, Lũ Lụt, Lũ quét, Sạt lở đất",
    heat_drought: "Nắng nóng, Hạn hán, Xâm nhập mặn",
    wind_fog: "Gió mạnh trên biển, Sương mù",
    storm_surge: "Nước dâng",
    extreme_other: "Lốc, Sét, Mưa đá, Rét hại, Sương muối",
    wildfire: "Cháy rừng tự nhiên",
    quake_tsunami: "Động đất, Sóng thần",
    recovery: "Khắc phục",
    
    // Legacy / Fallback
    flood: "Mưa lớn, Lũ, Lũ quét, Sạt lở đất",
    landslide: "Mưa lớn, Lũ Lụt, Lũ quét, Sạt lở đất",
    heavy_rain: "Mưa lớn, Lũ, Lũ quét, Sạt lở đất",
    earthquake: "Động đất, Sóng thần",
    tsunami: "Động đất, Sóng thần",
    wind_hail: "Lốc, Sét, Mưa đá, Rét hại, Sương muối", 
    extreme_weather: "Nắng nóng, Hạn hán, Xâm nhập mặn",
    
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
  return d.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });
}

/** Robust unescape for UI display */
export function cleanText(text) {
  if (!text) return "";
  const doc = new DOMParser().parseFromString(text, "text/html");
  return doc.documentElement.textContent;
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
