import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Search,
  User,
  Menu,
  X,
  Grid,
  Bell
} from "lucide-react";
import logoIge from "../assets/logo_ige.png";



export default function MainLayout({ children }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const isMapPage = location.pathname.startsWith("/map");

  const navigation = [
    { name: "TỔNG QUAN", href: "/", current: location.pathname === "/" },
    { name: "SỰ KIỆN", href: "/events", current: location.pathname.startsWith("/events") },
    { name: "BẢN ĐỒ", href: "/map", current: location.pathname === "/map" },
  ];

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
            <div className="flex items-center h-12">
                {/* Desktop/Tablet Nav */}
                <div className="flex h-full border-l border-white/20">
                    {navigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            className={`flex items-center justify-center px-6 text-sm font-bold uppercase tracking-wide border-r border-white/20 transition-colors ${
                                item.current
                                    ? "bg-[#258a9b] text-white"
                                    : "text-white hover:bg-[#258a9b]"
                            }`}
                        >
                            {item.name}
                        </Link>
                    ))}
                </div>
            </div>
        </div>
        
        {/* Mobile Menu Dropdown */}
        {isMobileMenuOpen && (
            <div className="md:hidden bg-[#2fa1b3] border-t border-[#258a9b]">
                <div className="px-2 pt-2 pb-3 space-y-1">
                    {navigation.map((item) => (
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
