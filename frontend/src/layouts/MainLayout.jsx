import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import {
  Search,
  User,
  Menu,
  X,
  AlertTriangle,
  Bell,
  LogOut,
  ShieldCheck,
  MapPin,
  Sun,
  Moon,
  Info,
  Activity,
  ArrowRight,
  ShieldAlert,
  Phone
} from "lucide-react";
import logoIge from "../assets/logo_ige.png";
import { putJson, API_BASE } from "../api.js";
import NotificationDropdown from "../components/NotificationDropdown";
import CrowdsourceModal from "../components/CrowdsourceModal";

const PROVINCES = [
  "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên", "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh", "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình", "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế", "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa", "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp", "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
].sort();

export default function MainLayout({ children }) {
  const [isDark, setIsDark] = useState(() => {
    // Default to Light Mode (false) unless explicitly set to dark
    return localStorage.getItem("theme") === "dark";
  });
  const [toasts, setToasts] = useState([]);
  const [user, setUser] = useState(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isCrowdsourceOpen, setIsCrowdsourceOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const isMapPage = location.pathname.startsWith("/map");

  useEffect(() => {
      if (isDark) {
          document.documentElement.classList.add("dark");
          localStorage.setItem("theme", "dark");
      } else {
          document.documentElement.classList.remove("dark");
          localStorage.setItem("theme", "light");
      }
  }, [isDark]);

  useEffect(() => {
    // Real-time WebSocket connection
    let ws;
    let reconnectTimer;

    const connect = () => {
        // Use API_BASE to derive WS URL to ensure consistency
        const wsBase = API_BASE.replace(/^http/, 'ws');
        const wsUrl = `${wsBase}/ws`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log("WS connected successfully to:", wsUrl);
        };
        
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "EVENT_UPSERT" && msg.data?.event_id) {
                    const data = msg.data;
                    const eventId = data.event_id;
                    const eventTitle = data.title;
                    
                    // [VISIBILITY FILTER]
                    // Only show 'Khẩn cấp' toasts to Guests/Users if the event is high quality
                    // (Confidence >= 0.8 OR Admin-verified)
                    const storedUserStr = localStorage.getItem("user");
                    let role = "guest";
                    try {
                        const u = JSON.parse(storedUserStr);
                        role = u?.role || "guest";
                    } catch (e) {}

                    const isHighQuality = (data.confidence >= 0.8) || (data.needs_verification === 0 && data.sources_count >= 2);
                    const isAdmin = role === "admin";
                    const isKnownType = !["unknown", "other"].includes(data.disaster_type);

                    if (!isAdmin && (!isHighQuality || !isKnownType)) {
                        return; // Skip notification for non-admins if quality is low
                    }

                    setToasts(prev => {
                        // Prevent duplicate toasts for the same event already visible
                        if (prev.some(t => t.event_id === eventId)) return prev;
                        
                        const newId = `${eventId}_${Date.now()}`;
                        const newToast = {
                            id: newId,
                            title: eventTitle,
                            event_id: eventId,
                            province: msg.data.province
                        };

                        // Auto-remove after 8s
                        setTimeout(() => {
                            setToasts(current => current.filter(t => t.id !== newId));
                        }, 8000);

                        return [newToast, ...prev].slice(0, 3);
                    });
                }
            } catch (e) { console.error("WS parse error", e); }
        };
        
        ws.onclose = () => {
            console.log("WS closed. Reconnecting in 5s...");
            reconnectTimer = setTimeout(connect, 5000);
        };
        
        ws.onerror = (err) => {
            console.error("WS Error", err);
            ws.close();
        };
    };

    connect();
    return () => {
        if (ws) ws.close();
        clearTimeout(reconnectTimer);
    };
  }, []);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        if (parsed && typeof parsed === 'object') {
            setUser(parsed);
        }
      } catch (e) {
        console.error("Session corruption:", e);
        localStorage.removeItem("user");
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("access_token");
    setUser(null);
    navigate("/login");
  };

  const handleProvinceChange = async (prov) => {
    let updated;
    if (user && user.role !== 'guest') {
        try {
            updated = await putJson("/api/auth/me/preferences", { favorite_province: prov });
        } catch (err) {
            console.error("Failed to update province", err);
            updated = { ...user, favorite_province: prov };
        }
    } else {
        // Guest mode
        updated = { ...(user || {}), favorite_province: prov, role: 'guest' };
    }
    
    setUser(updated);
    localStorage.setItem("user", JSON.stringify(updated));
    window.dispatchEvent(new Event("storage"));
  };


  const userNavigation = [
    { name: "TỔNG QUAN", href: "/", current: location.pathname === "/" },
    { name: "SỰ KIỆN", href: "/events", current: location.pathname.startsWith("/events") },
    { name: "BẢN ĐỒ", href: "/map", current: location.pathname === "/map" },
    { name: "CỨU HỘ", href: "/rescue", current: location.pathname === "/rescue" },
  ];

  const adminNavigation = user?.role === "admin" ? [
    { name: "QUẢN TRỊ & DUYỆT TIN", href: "/admin/logs", current: location.pathname.startsWith("/admin/logs") },
    { name: "SỨC KHỎE CRAWLER", href: "/admin/crawler", current: location.pathname === "/admin/crawler" },
    { name: "BÁO CÁO CỘNG ĐỒNG", href: "/admin/reports", current: location.pathname.startsWith("/admin/reports") },
  ] : [];

  const [showScroll, setShowScroll] = useState(false);
  useEffect(() => {
    const handleScroll = () => setShowScroll(window.scrollY > 400);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 dark:bg-[#0b1120] font-sans transition-colors duration-300">
      <Helmet>
        <title>BÁO TỔNG HỢP RỦI RO THIÊN TAI - Theo dõi rủi ro thời gian thực</title>
        <meta name="description" content="Hệ thống giám sát và tổng hợp tin tức thiên tai tại Việt Nam thời gian thực. Cập nhật bão, lũ, sạt lở từ các nguồn tin chính thống." />
        <meta name="keywords" content="thiên tai, bão lũ, thời tiết Việt Nam, cứu hộ, trực tuyến, tin tức khẩn cấp" />
        <meta property="og:title" content="BÁO TỔNG HỢP RỦI RO THIÊN TAI - Hệ thống giám sát thiên tai" />
        <meta property="og:description" content="Cập nhật tin tức thiên tai 24/7 từ 63 tỉnh thành Việt Nam." />
        <meta property="og:type" content="website" />
      </Helmet>
      {/* Top Header (White / Dark) */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 flex-none z-30 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            {/* Logo / Brand */}
            <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="flex items-center gap-2">
                    {/* Icon Logo */}
                        <div className="w-12 h-12 flex items-center justify-center overflow-hidden bg-white rounded-lg p-1">
                            <img 
                                src={logoIge} 
                                alt="IGE Logo" 
                                className="w-full h-full object-contain" 
                            />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-xl font-black tracking-tighter text-slate-800 dark:text-white leading-none">
                                BÁO TỔNG HỢP <span className="text-[#2fa1b3] dark:text-[#4fd1e3]">RỦI RO THIÊN TAI</span>
                            </span>
                            <span className="text-[9px] font-bold text-[#2fa1b3] dark:text-[#4fd1e3] tracking-[0.2em] uppercase mt-0.5">
                                VIETNAM DISASTER SURVEILLANCE
                            </span>
                        </div>
                </Link>
            </div>

            {/* Desktop Actions (Right) */}
            <div className="hidden md:flex items-center gap-3">
               <button 
                  onClick={() => setIsDark(!isDark)}
                  className="w-10 h-10 flex items-center justify-center rounded-xl bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-[#2fa1b3] hover:bg-[#2fa1b3]/10 transition-all border border-slate-200 dark:border-slate-700 shadow-sm"
                  title={isDark ? "Chế độ sáng" : "Chế độ tối"}
               >
                  {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
               </button>

               <div className="h-8 w-px bg-slate-100 dark:bg-slate-800 mx-2" />

               {user && user.role !== 'guest' ? (
                 <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{user.role}</span>
                      <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{user.full_name || user.email}</span>
                    </div>
                    <button 
                        onClick={handleLogout}
                        className="w-10 h-10 flex items-center justify-center rounded-xl bg-red-50 dark:bg-red-900/20 text-red-500 hover:bg-red-500 hover:text-white transition-all border border-red-100 dark:border-red-900/30 shadow-sm"
                        title="Đăng xuất"
                    >
                        <LogOut className="w-5 h-5" />
                    </button>
                 </div>
               ) : (
                 <div className="flex items-center gap-2">
                    <Link to="/login" className="px-4 py-2 text-sm font-bold text-slate-600 dark:text-slate-300 hover:text-[#2fa1b3] transition-colors">Đăng nhập</Link>
                    <Link to="/register" className="px-4 py-2 text-sm font-bold bg-[#2fa1b3] text-white rounded-xl hover:bg-[#258a9b] transition-all shadow-lg shadow-[#2fa1b3]/20">Đăng ký</Link>
                 </div>
               )}
            </div>

            {/* Mobile Menu Button */}
            <div className="flex items-center md:hidden gap-3">
                <button 
                    onClick={() => setIsDark(!isDark)}
                    className="p-2 text-slate-500 dark:text-slate-400"
                >
                    {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                </button>
                <button 
                    className="p-2 text-slate-700 dark:text-slate-200"
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                >
                    {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
            </div>
        </div>
      </header>

      {/* Navigation Bar (Teal - Bao Moi Style) */}
      <nav className="bg-[#2fa1b3] shadow-md sticky top-0 z-50 flex-none">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center h-12 justify-between">
                {/* Desktop/Tablet Nav */}
                <div className="flex h-full border-l border-white/20">
                    {userNavigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            className={`flex items-center px-4 h-full text-xs font-black tracking-widest uppercase transition-all border-r border-white/20 ${
                                item.current
                                    ? "bg-[#258a9b] text-white shadow-inner"
                                    : "text-white/80 hover:bg-[#258a9b] hover:text-white"
                            }`}
                        >
                            {item.name === "CỨU HỘ" && <ShieldAlert className="w-3.5 h-3.5 mr-2 text-red-100 group-hover:text-white" />}
                            {item.name}
                        </Link>
                    ))}


                    
                    {adminNavigation.length > 0 && adminNavigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            className={`flex items-center px-4 h-full text-xs font-black tracking-widest uppercase transition-all border-r border-white/20 border-l-[3px] border-l-yellow-400 ${
                                item.current
                                    ? "bg-slate-800 text-yellow-300 shadow-inner"
                                    : "bg-slate-900/40 text-yellow-400/80 hover:bg-slate-800 hover:text-yellow-300"
                            }`}
                        >
                            <ShieldCheck className="w-3.5 h-3.5 mr-2" />
                            {item.name}
                        </Link>
                    ))}
                </div>



                {/* Account Actions (Desktop) */}
                <div className="hidden md:flex items-center gap-2 h-full">
                    {/* Crowdsourcing & Notifications (Logged in users only) */}
                    {user?.role !== "admin" && (
                            <button 
                                onClick={() => setIsCrowdsourceOpen(true)}
                                className="flex items-center gap-2 px-4 h-full text-white text-[10px] font-black hover:bg-white/10 transition-colors border-l border-white/20 uppercase tracking-tighter"
                            >
                                <AlertTriangle className="w-3.5 h-3.5 text-yellow-300" />
                                Đóng góp hiện trường
                            </button>
                    )}
                    {user && user.role !== 'guest' && (
                        <>
                            <div className="h-full border-l border-white/20 flex items-center px-2">
                                <NotificationDropdown isOpen={isNotifOpen} setIsOpen={setIsNotifOpen} user={user} />
                            </div>
                        </>
                    )}

                    {user && user.role !== 'guest' ? (
                        <div className="flex items-center h-full">
                            <span className="flex items-center gap-2 px-4 h-full text-white text-xs font-bold border-l border-white/20">
                                {user.role === 'admin' ? <ShieldCheck className="w-4 h-4 text-yellow-300" /> : <User className="w-4 h-4" />}
                                {(user.full_name || user.email || "").toUpperCase()}
                            </span>
                            <button 
                                onClick={handleLogout}
                                className="flex items-center gap-2 px-4 h-full text-white text-sm font-bold hover:bg-red-500 transition-colors border-l border-r border-white/20"
                            >
                                <LogOut className="w-4 h-4" />
                                ĐĂNG XUẤT
                            </button>
                        </div>
                    ) : (
                        <>
                            <Link 
                                to="/login" 
                                className="flex items-center gap-2 px-4 h-full text-white text-sm font-bold hover:bg-[#258a9b] transition-colors border-l border-white/20"
                            >
                                <User className="w-4 h-4" />
                                ĐĂNG NHẬP
                            </Link>
                            <Link 
                                to="/register" 
                                className="flex items-center gap-2 px-4 h-full text-white text-sm font-bold hover:bg-[#258a9b] transition-colors border-l border-r border-white/20 bg-white/10"
                            >
                                ĐĂNG KÝ
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </div>
        
        {/* Mobile Menu Dropdown */}
        {isMobileMenuOpen && (
            <div className="md:hidden bg-[#2fa1b3] dark:bg-slate-900 border-t border-[#258a9b] dark:border-slate-800">
                <div className="px-2 pt-2 pb-3 space-y-1">
                    {userNavigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={`block px-3 py-2 rounded-md text-sm font-bold ${
                                item.current
                                    ? "bg-[#258a9b] text-white"
                                    : "text-white hover:bg-[#258a9b]"
                            }`}
                        >
                            {item.name}
                        </Link>
                    ))}
                    {adminNavigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-bold mt-2 ${
                                item.current
                                    ? "bg-slate-800 text-yellow-300"
                                    : "bg-slate-900/20 text-yellow-400 hover:bg-slate-800 hover:text-yellow-300"
                            }`}
                        >
                            <ShieldCheck className="w-4 h-4" />
                            {item.name}
                        </Link>
                    ))}
                    {user?.role !== "admin" && (
                            <button 
                                onClick={() => { setIsCrowdsourceOpen(true); setIsMobileMenuOpen(false); }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm font-bold text-white bg-red-600/30 hover:bg-red-600/50 mt-2"
                            >
                                <AlertTriangle className="w-4 h-4 text-yellow-300" />
                                ĐÓNG GÓP HIỆN TRƯỜNG
                            </button>
                    )}
                    {user && user.role !== 'guest' && (
                        <>
                            <button 
                                onClick={() => { setIsNotifOpen(true); setIsMobileMenuOpen(false); }}
                                className="flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm font-bold text-white hover:bg-[#258a9b]"
                            >
                                <Bell className="w-4 h-4" />
                                THÔNG BÁO
                            </button>
                        </>
                    )}
                    <div className="pt-2 mt-2 border-t border-[#258a9b]">
                        {user ? (
                            <>
                                <div className="px-3 py-2 text-xs font-bold text-white/70 uppercase">
                                    {user.full_name || user.email}
                                </div>
                                <button
                                    onClick={() => { handleLogout(); setIsMobileMenuOpen(false); }}
                                    className="block w-full text-left px-3 py-2 rounded-md text-sm font-bold text-white hover:bg-red-500"
                                >
                                    ĐĂNG XUẤT
                                </button>
                            </>
                        ) : (
                            <>
                                <Link
                                    to="/login"
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className="block px-3 py-2 rounded-md text-sm font-bold text-white hover:bg-[#258a9b]"
                                >
                                    ĐĂNG NHẬP
                                </Link>
                                <Link
                                    to="/register"
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className="block px-3 py-2 rounded-md text-sm font-bold text-white hover:bg-[#258a9b]"
                                >
                                    ĐĂNG KÝ
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </div>
        )}
      </nav>

      {/* Main Content */}
      <main className={`flex-1 flex flex-col ${isMapPage ? 'w-full' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full'}`}>
        {children}
      </main>

      {/* Footer (Simplified) */}
      {/* Footer (Professional) */}
      <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 mt-auto flex-none">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-sm">
                
                {/* Column 1: Liên hệ */}
                <div className="md:col-span-2 space-y-3">
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">Liên hệ</h3>
                    <ul className="space-y-2 text-slate-600 dark:text-slate-400">
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Giới thiệu</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Điều khoản sử dụng</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Chính sách bảo mật</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Quảng cáo</a></li>
                    </ul>
                </div>

                {/* Column 2: Khác */}
                <div className="md:col-span-2 space-y-3">
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">Khác</h3>
                    <ul className="space-y-2 text-slate-600 dark:text-slate-400">
                        <li><Link to="/map" className="hover:text-[#2fa1b3] transition-colors">Bản đồ rủi ro</Link></li>
                        <li><Link to="/events" className="hover:text-[#2fa1b3] transition-colors">Dòng sự kiện</Link></li>
                        <li><Link to="/rescue" className="hover:text-red-500 font-bold transition-colors">Cứu hộ khẩn cấp</Link></li>
                        <li><Link to="/admin/logs" className="hover:text-[#2fa1b3] transition-colors">Xác minh tin (Admin)</Link></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">RSS Feeds</a></li>
                    </ul>
                </div>

                {/* Column 3: License / Info */}
                <div className="md:col-span-8 md:text-right space-y-2 text-slate-500 dark:text-slate-500 text-xs leading-relaxed border-t md:border-t-0 border-slate-100 dark:border-slate-800 pt-4 md:pt-0">
                    <p>
                        <span className="font-bold text-slate-900 dark:text-slate-200 uppercase text-sm block mb-1">
                            BÁO TỔNG HỢP RỦI RO THIÊN TAI - VIETNAM DISASTER SURVEILLANCE
                        </span>
                        <span>Đơn vị thiết lập: Nhóm nghiên cứu & Phát triển.</span>
                    </p>
                    <p>
                         Hệ thống tự động tổng hợp tin tức thiên tai từ các nguồn chính thống (KTTV Quốc gia, Báo Chính Phủ, TTXVN, v.v...) nhằm cung cấp cái nhìn toàn cảnh về tình hình thiên tai tại Việt Nam.
                    </p>
                    <p>
                        Địa chỉ: Hà Nội, Việt Nam. Email: contact@vietndisasterwatch.com <br/>
                    </p>
                    <p className="italic mt-2">
                        Lưu ý: Các thông tin dự báo chỉ mang tính chất tham khảo, vui lòng theo dõi các bản tin chính thức từ cơ quan chức năng địa phương.
                    </p>
                </div>
            </div>
        </div>
      </footer>

      {/* Real-time Notification Toast Container */}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
        {toasts.map(toast => (
          <div 
            key={toast.id}
            className="pointer-events-auto bg-white dark:bg-slate-800 border-l-4 border-red-500 rounded-xl shadow-2xl p-4 flex gap-4 animate-in slide-in-from-right duration-500 group relative overflow-hidden ring-1 ring-slate-200 dark:ring-slate-700"
          >
            <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 dark:bg-red-500/10 rounded-full translate-x-12 -translate-y-12 blur-2xl" />
            
            <div className="w-10 h-10 rounded-full bg-red-50 dark:bg-red-900/30 flex-none flex items-center justify-center text-red-600 dark:text-red-400">
              <AlertTriangle className="w-5 h-5 animate-bounce" />
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-black uppercase tracking-tighter text-red-500 bg-red-50 dark:bg-red-900/50 px-1.5 py-0.5 rounded">
                  Khẩn cấp
                </span>
                <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">
                  Vừa xong
                </span>
              </div>
              <h4 className="text-xs font-black text-slate-900 dark:text-white truncate">
                {toast.title}
              </h4>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                Khu vực: <span className="font-bold text-slate-700 dark:text-slate-200">{toast.province}</span>
              </p>
              
              <Link 
                to={`/events/${toast.event_id}`}
                onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
                className="mt-2 flex items-center gap-1 text-[10px] font-bold text-[#2fa1b3] hover:text-[#258a9b] dark:text-[#4fd1e3] transition-colors"
              >
                XEM CHI TIẾT <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <button 
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
              className="absolute top-2 right-2 p-1 text-slate-300 hover:text-slate-500 dark:text-slate-600 dark:hover:text-slate-400"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
      
      {/* Scroll to Top */}
      {showScroll && (
        <button 
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="fixed bottom-6 left-6 z-40 p-3 bg-white dark:bg-slate-800 text-[#2fa1b3] rounded-full shadow-2xl border border-slate-200 dark:border-slate-700 hover:scale-110 active:scale-90 transition-all animate-bounce"
        >
          <ArrowRight className="w-6 h-6 -rotate-90" />
        </button>
      )}

      {/* Crowdsourcing Modal */}
      <CrowdsourceModal 
        isOpen={isCrowdsourceOpen} 
        onClose={() => setIsCrowdsourceOpen(false)} 
        user={user} 
      />
    </div>
  );
}
