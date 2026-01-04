export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function getJson(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};
  const res = await fetch(API_BASE + path, { 
    ...options,
    headers: { ...headers, ...options.headers }
  });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("storage"));
    }
    const err = new Error(`API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function deleteJson(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};
  const res = await fetch(API_BASE + path, { 
    ...options,
    method: "DELETE", 
    headers: { ...headers, ...options.headers }
  });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("storage"));
    }
    let errorDetail = "";
    try {
        const errData = await res.json();
        errorDetail = errData.detail || "";
    } catch(e) {}
    
    const err = new Error(errorDetail || `API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return true;
}

export async function putJson(path, payload, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { 
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
  const res = await fetch(API_BASE + path, { 
    ...options,
    method: "PUT", 
    headers: { ...headers, ...options.headers }, 
    body: JSON.stringify(payload) 
  });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("storage"));
    }
    const errData = await res.json().catch(() => ({}));
    const err = new Error(errData.detail || `API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function postJson(path, payload, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { 
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
  const res = await fetch(API_BASE + path, { 
    ...options,
    method: "POST", 
    headers: { ...headers, ...options.headers }, 
    body: JSON.stringify(payload) 
  });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("storage"));
    }
    const errData = await res.json().catch(() => ({}));
    const err = new Error(errData.detail || `API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function patchJson(path, payload = {}, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { 
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
  const res = await fetch(API_BASE + path, { 
    ...options,
    method: "PATCH", 
    headers: { ...headers, ...options.headers }, 
    body: JSON.stringify(payload) 
  });
  if (!res.ok) {
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("storage"));
    }
    const errData = await res.json().catch(() => ({}));
    const err = new Error(errData.detail || `API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
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
    // 14 Official Disaster Types
    storm: "Bão, ATNĐ",
    flood: "Lũ lụt",
    flash_flood: "Lũ quét, Lũ ống",
    landslide: "Sạt lở",
    subsidence: "Sụt lún đất",
    drought: "Hạn hán",
    salinity: "Xâm nhập mặn",
    extreme_weather: "Mưa lớn, Lốc, Sét, Mưa Đá",
    heatwave: "Nắng nóng",
    cold_surge: "Rét hại, Sương muối",
    earthquake: "Động đất",
    tsunami: "Sóng thần",
    storm_surge: "Nước dâng",
    wildfire: "Cháy rừng",
    erosion: "Xói lở",

    // 2 Special Groups
    warning_forecast: "Cảnh báo, dự báo",
    recovery: "Khắc phục hậu quả",

    unknown: "Chưa phân loại",
  };
  return map[t] || t;
}

export function fmtVndBillion(x) {
  if (x === null || x === undefined || x === "") return "—";
  const val = typeof x === "string" ? parseFloat(x) : x;
  if (isNaN(val)) return "—";
  return `${val.toLocaleString("vi-VN")} tỷ`;
}

/** 
 * Checks if image is a generic placeholder or news logo 
 */
export const isJunkImage = (url) => {
  if (!url) return true;
  const junkPatterns = [
      'googleusercontent.com', 
      'gstatic.com', 
      'news_logo', 
      'default_image',
      'placeholder',
      'tabler-icons',
      'triangle.svg',
      'droplet.svg',
      'fallback',
      'no-image'
  ];
  return junkPatterns.some(p => url.toLowerCase().includes(p));
};

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

/** Helper to normalize string for search (diacritics removed, lowercase) */
export function normalizeStr(str, removeSpaces = false) {
    if (!str) return "";
    let res = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (removeSpaces) res = res.replace(/\s+/g, '');
    return res;
}

export function fmtTimeAgo(s) {
  const d = new Date(s);
  const now = new Date();
  const seconds = Math.max(0, Math.floor((now - d) / 1000));

  if (seconds < 60) return "Vừa xong";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} ngày trước`;

  return fmtDate(s);
}
