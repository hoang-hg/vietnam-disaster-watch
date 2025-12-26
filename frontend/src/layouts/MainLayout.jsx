import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Search,
  User,
  Menu,
  X,
  Grid,
  Bell,
  LogOut,
  ShieldCheck,
  MapPin,
  Mail
} from "lucide-react";
import logoIge from "../assets/logo_ige.png";
import { putJson } from "../api.js";

const PROVINCES = [
    "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên",
  "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh",
  "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình",
  "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế",
  "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa",
  "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp",
  "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
].sort();

export default function MainLayout({ children }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();
  const isMapPage = location.pathname.startsWith("/map");

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

  const toggleEmailNotifications = async () => {
    if (!user || user.role === 'guest') {
        alert("Vui lòng đăng nhập để sử dụng tính năng nhận tin qua Email.");
        return;
    }
    try {
        const newVal = !user.email_notifications;
        const updatedUser = await putJson("/api/auth/me/preferences", { email_notifications: newVal });
        setUser(updatedUser);
        localStorage.setItem("user", JSON.stringify(updatedUser));
        window.dispatchEvent(new Event("storage"));
    } catch (err) {
        console.error("Failed to update email preferences", err);
    }
  };

  const userNavigation = [
    { name: "TỔNG QUAN", href: "/", current: location.pathname === "/" },
    { name: "SỰ KIỆN", href: "/events", current: location.pathname.startsWith("/events") },
    { name: "BẢN ĐỒ", href: "/map", current: location.pathname === "/map" },
  ];

  const adminNavigation = user?.role === "admin" ? [
    { name: "QUẢN TRỊ & DUYỆT TIN", href: "/admin/logs", current: location.pathname.startsWith("/admin/logs") },
  ] : [];

  return (
    <div className="flex flex-col min-h-screen bg-slate-100 font-sans">
      {/* Top Header (White) */}
      <header className="bg-white border-b border-slate-100 flex-none">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            {/* Logo / Brand */}
            <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="flex items-center gap-2">
                    {/* Icon Logo */}
                        <div className="w-12 h-12 flex items-center justify-center overflow-hidden">
                            <img 
                                src={logoIge} 
                                alt="IGE Logo" 
                                className="w-full h-full object-contain" 
                                style={{ mixBlendMode: 'multiply' }}
                            />
                        </div>
                        {/* Text Logo */}
                        <span className="text-2xl font-black tracking-tighter text-[#2fa1b3] uppercase leading-none">
                            BÁO TỔNG HỢP RỦI RO THIÊN TAI 
                            {user?.role === 'admin' && (
                                <span className="ml-2 bg-slate-900 text-yellow-400 text-[10px] px-2 py-0.5 rounded-full border border-yellow-400/50 align-middle tracking-widest font-black shadow-lg shadow-yellow-400/10 animate-pulse">
                                    ADMIN
                                </span>
                            )}
                        </span>
                </Link>
            </div>

            {/* Mobile Menu Button - Moved to right since actions are gone */}
            <div className="flex items-center md:hidden">
                <button 
                    className="p-2 text-slate-700"
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
                            {item.name}
                        </Link>
                    ))}

                    {/* Province Selector (Area of Interest) - Moved next to Nav items */}
                    <div className="flex items-center gap-2 px-4 border-r border-white/20 h-full bg-black/10">
                        <MapPin className="w-3.5 h-3.5 text-white/70" />
                        <select 
                            value={user?.favorite_province || ""}
                            onChange={(e) => handleProvinceChange(e.target.value)}
                            className="bg-transparent text-white text-[11px] font-black uppercase outline-none cursor-pointer hover:text-yellow-300 transition-colors"
                        >
                            <option value="" className="text-slate-900">Toàn quốc</option>
                            {PROVINCES.map(p => (
                                <option key={p} value={p} className="text-slate-900">{p}</option>
                            ))}
                        </select>
                    </div>
                    
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


                {/* Email Notification Toggle */}
                {user && user.role !== 'guest' && (
                    <div className="flex items-center h-full border-l border-white/20">
                        <button 
                            onClick={toggleEmailNotifications}
                            title={user.email_notifications ? "Đang bật nhận tin qua Email" : "Đã tắt nhận tin qua Email"}
                            className={`flex items-center gap-1.5 px-4 h-full transition-all group ${user.email_notifications ? "text-yellow-300" : "text-white/40 hover:text-white"}`}
                        >
                            {user.email_notifications ? (
                                <Mail className="w-4 h-4 animate-pulse" />
                            ) : (
                                <Mail className="w-4 h-4 opacity-40" />
                            )}
                            <span className="text-[10px] font-black uppercase">
                                {user.email_notifications ? "Bật" : "Tắt"}
                            </span>
                        </button>
                    </div>
                )}

                {/* Account Actions (Desktop) */}
                <div className="hidden md:flex items-center gap-2 h-full">
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
            <div className="md:hidden bg-[#2fa1b3] border-t border-[#258a9b]">
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
                    <div className="pt-2 mt-2 border-t border-[#258a9b]">
                        {user ? (
                            <>
                                <div className="px-3 py-2 text-xs font-bold text-white/70 uppercase">
                                    Đang đăng nhập: {user.full_name || user.email} ({user.role || "user"})
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
      <footer className="bg-white border-t border-slate-200 mt-auto flex-none">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-sm">
                
                {/* Column 1: Liên hệ */}
                <div className="md:col-span-2 space-y-3">
                    <h3 className="font-bold text-slate-900 uppercase tracking-wider">Liên hệ</h3>
                    <ul className="space-y-2 text-slate-600">
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Giới thiệu</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Điều khoản sử dụng</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Chính sách bảo mật</a></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">Quảng cáo</a></li>
                    </ul>
                </div>

                {/* Column 2: Khác */}
                <div className="md:col-span-2 space-y-3">
                    <h3 className="font-bold text-slate-900 uppercase tracking-wider">Khác</h3>
                    <ul className="space-y-2 text-slate-600">
                        <li><Link to="/map" className="hover:text-[#2fa1b3] transition-colors">Bản đồ rủi ro</Link></li>
                        <li><Link to="/events" className="hover:text-[#2fa1b3] transition-colors">Dòng sự kiện</Link></li>
                        <li><Link to="/admin/logs" className="hover:text-[#2fa1b3] transition-colors">Xác minh tin (Admin)</Link></li>
                        <li><a href="#" className="hover:text-[#2fa1b3] transition-colors">RSS Feeds</a></li>
                    </ul>
                </div>

                {/* Column 3: License / Info (Right aligned equivalent) */}
                <div className="md:col-span-8 md:text-right space-y-2 text-slate-500 text-xs leading-relaxed border-t md:border-t-0 border-slate-100 pt-4 md:pt-0">
                    <p>
                        <span className="font-bold text-slate-900 uppercase text-sm block mb-1">
                            BÁO TỔNG HỢP RỦI RO THIÊN TAI - VIỆT NAM DISASTER WATCHING
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
    </div>
  );
}
