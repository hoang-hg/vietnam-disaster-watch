/**
 * Centralized constants for consistent behavior across the app
 */

// Pagination
export const ITEMS_PER_PAGE = {
  EVENTS: 20,
  ARTICLES: 20,
  HOTLINES: 15,
  ADMIN_REPORTS: 20,
  ADMIN_SKIP_LOGS: 20,
  DEFAULT: 20
};

// Loading Messages
export const LOADING_MESSAGES = {
  DELETING: "Đang xóa...",
  SAVING: "Đang lưu...",
  EXPORTING: "Đang xuất...",
  APPROVING: "Đang duyệt...",
  LOADING: "Đang tải...",
  PROCESSING: "Đang xử lý...",
  UPLOADING: "Đang tải lên...",
  SUBMITTING: "Đang gửi..."
};

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK: "Lỗi kết nối mạng. Vui lòng kiểm tra kết nối internet.",
  UNAUTHORIZED: "Bạn không có quyền thực hiện thao tác này",
  NOT_FOUND: "Không tìm thấy dữ liệu",
  SERVER_ERROR: "Lỗi server, vui lòng thử lại sau",
  VALIDATION: "Dữ liệu không hợp lệ",
  TIMEOUT: "Yêu cầu hết thời gian chờ",
  UNKNOWN: "Đã có lỗi xảy ra",
  SESSION_EXPIRED: "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại."
};

// Success Messages
export const SUCCESS_MESSAGES = {
  SAVED: "Lưu thành công!",
  DELETED: "Xóa thành công!",
  EXPORTED: "Xuất dữ liệu thành công!",
  APPROVED: "Duyệt thành công!",
  UPDATED: "Cập nhật thành công!",
  CREATED: "Tạo mới thành công!",
  UPLOADED: "Tải lên thành công!",
  SUBMITTED: "Gửi thành công!"
};

// API Configuration
export const API_CONFIG = {
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
  DEBOUNCE_DELAY: 300 // ms for search inputs
};

// Toast Configuration
export const TOAST_DURATION = {
  SHORT: 2000,
  MEDIUM: 3000,
  LONG: 5000
};

// Date Formats
export const DATE_FORMATS = {
  FULL: "DD/MM/YYYY HH:mm:ss",
  DATE_ONLY: "DD/MM/YYYY",
  TIME_ONLY: "HH:mm",
  ISO: "YYYY-MM-DD"
};

// File Upload
export const FILE_UPLOAD = {
  MAX_SIZE: 5 * 1024 * 1024, // 5MB
  ALLOWED_TYPES: {
    IMAGES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    DOCUMENTS: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
  }
};

// Chart Configuration
export const CHART_CONFIG = {
  MOBILE_BREAKPOINT: 640,
  MOBILE_HEIGHT: 256,
  DESKTOP_HEIGHT: 384,
  MOBILE_BAR_SIZE: 18,
  DESKTOP_BAR_SIZE: 24,
  MOBILE_FONT_SIZE: 10,
  DESKTOP_FONT_SIZE: 12
};

// Storage Keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  USER: "user",
  THEME: "theme",
  LANGUAGE: "language"
};

// Routes
export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  EVENTS: "/events",
  EVENT_DETAIL: "/events/:id",
  MAP: "/map",
  RESCUE: "/rescue",
  ABOUT: "/about",
  LOGIN: "/login",
  REGISTER: "/register",
  ADMIN_REPORTS: "/admin/reports",
  ADMIN_SKIP_LOGS: "/admin/skip-logs",
  CRAWLER_DASHBOARD: "/admin/crawler"
};
