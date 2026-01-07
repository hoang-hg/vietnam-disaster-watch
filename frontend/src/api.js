import { DISASTER_METADATA } from "./theme.js";

// For Docker: VITE_API_BASE is set to empty string, use relative paths
// For local dev: VITE_API_BASE is undefined, use localhost:8000
export const API_BASE =
  import.meta.env.VITE_API_BASE !== undefined 
    ? import.meta.env.VITE_API_BASE 
    : "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = {
    ...options.headers,
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  };

  if (["POST", "PUT", "PATCH"].includes(options.method) && options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(API_BASE + path, { ...options, headers });

  if (!res.ok) {
    let errorDetail = "";
    try {
      const errData = await res.json();
      errorDetail = errData.detail || JSON.stringify(errData);
    } catch (e) {
      errorDetail = await res.text().catch(() => "Unknown error");
    }

    if (res.status === 401) {
      console.error(`[AUTH] 401 Unauthorized at ${path}. Detail:`, errorDetail);
      
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.dispatchEvent(new Event("storage"));
    }
    
    const err = new Error(errorDetail || `API error ${res.status}`);
    err.status = res.status;
    throw err;
  }

  return res.status === 204 ? true : res.json();
}

export async function getJson(path, options = {}) {
  return request(path, { ...options, method: "GET" });
}

export async function deleteJson(path, options = {}) {
  return request(path, { ...options, method: "DELETE" });
}

export async function putJson(path, payload, options = {}) {
  return request(path, { ...options, method: "PUT", body: JSON.stringify(payload) });
}

export async function postJson(path, payload, options = {}) {
  return request(path, { ...options, method: "POST", body: (payload instanceof FormData) ? payload : JSON.stringify(payload) });
}

export async function patchJson(path, payload = {}, options = {}) {
  return request(path, { ...options, method: "PATCH", body: JSON.stringify(payload) });
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

export async function changePassword(currentPassword, newPassword) {
  return postJson("/api/auth/change-password", { 
    current_password: currentPassword, 
    new_password: newPassword 
  });
}

export async function resetPassword(email, newPassword) {
  return postJson("/api/auth/reset-password", { 
    email: email, 
    new_password: newPassword 
  });
}

export function fmtType(t) {
  return DISASTER_METADATA[t]?.label || t;
}

export function getDisasterMeta(t) {
  return DISASTER_METADATA[t] || DISASTER_METADATA.unknown;
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

/** Robust unescape for UI display - Optimized */
const _domParser = new DOMParser();
export function cleanText(text) {
  if (!text) return "";
  // Optimization: Skip parsing if no HTML entities or tags are suspected
  if (!text.includes('&') && !text.includes('<')) return text;
  
  return _domParser.parseFromString(text, "text/html").documentElement.textContent;
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
