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

export default function MainLayout({ children }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navigation = [
    { name: "TỔNG QUAN", href: "/", current: location.pathname === "/" },
    { name: "SỰ KIỆN", href: "/events", current: location.pathname.startsWith("/events") },
    { name: "BẢN ĐỒ", href: "/map", current: location.pathname === "/map" },
  ];

  return (
    <div className="min-h-screen bg-slate-100 font-sans">
      {/* Top Header (White) */}
      <header className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            {/* Logo / Brand */}
            <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="flex items-center gap-2">
                    {/* Icon Logo */}
                    <div className="w-10 h-10 bg-[#2fa1b3] rounded-lg flex items-center justify-center text-white shadow-sm">
                        <Bell className="w-6 h-6 fill-current" />
                    </div>
                    {/* Text Logo */}
                    <span className="text-2xl font-black tracking-tighter text-[#2fa1b3] uppercase leading-none">
                        BÁO CẢNH BÁO <span className="text-[#e04f23]">RỦI RO THIÊN TAI</span>
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
      <nav className="bg-[#2fa1b3] shadow-md sticky top-0 z-50">
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
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer (Simplified) */}
      <footer className="bg-white border-t border-slate-200 mt-auto py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-500 text-sm">
            <p className="font-bold text-slate-700 uppercase mb-2">Báo Cảnh Báo Thiên Tai - Viet Disaster Watch</p>
            <p>Tổng hợp tin tức thiên tai tự động từ các nguồn chính thống.</p>
        </div>
      </footer>
    </div>
  );
}
