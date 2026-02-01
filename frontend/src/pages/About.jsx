import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Info, Server, ShieldCheck, Zap, Users } from 'lucide-react';

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12 font-sans">
      <Link 
        to="/" 
        className="inline-flex items-center text-sm font-bold text-slate-500 hover:text-[#2fa1b3] mb-8 transition-colors group"
      >
        <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
        Quay lại trang chính
      </Link>

      <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
        {/* Header Section */}
        <div className="p-8 md:p-12 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
          <div className="w-16 h-16 bg-[#2fa1b3]/10 rounded-2xl flex items-center justify-center mb-6 text-[#2fa1b3]">
            <Info className="w-8 h-8" />
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white mb-4">
            Giới thiệu hệ thống
          </h1>
          <p className="text-slate-600 dark:text-slate-400 text-lg leading-relaxed max-w-3xl">
            Hệ thống <strong>Báo tổng hợp rủi ro thiên tai</strong> là giải pháp công nghệ tiên tiến nhằm giám sát, tổng hợp và cảnh báo sớm các loại hình thiên tai tại Việt Nam.
          </p>
        </div>

        <div className="p-8 md:p-12 space-y-12">
          {/* Mission Section */}
          <section>
            <h2 className="text-2xl font-black text-slate-900 dark:text-white mb-6">Sứ mệnh & Tầm nhìn</h2>
            <div className="text-slate-600 dark:text-slate-400 leading-relaxed space-y-4 text-base">
              <p>
                Việt Nam là một trong những quốc gia chịu ảnh hưởng nặng nề nhất bởi biến đổi khí hậu. Các hiện tượng thời tiết cực đoan như bão, lũ lụt, sạt lở đất diễn biến ngày càng phức tạp, khó lường.
              </p>
              <p>
                Với sứ mệnh <strong>"Vì một Việt Nam an toàn hơn"</strong>, Viện Địa công nghệ và Môi trường đã phát triển hệ thống này nhằm cung cấp bức tranh toàn cảnh, thời gian thực về tình hình thiên tai trên cả nước, giúp cộng đồng và cơ quan chức năng chủ động ứng phó.
              </p>
            </div>
          </section>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl flex items-center justify-center mb-4">
                <Server className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Dữ liệu chính xác</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                Tự động thu thập và tổng hợp tin tức từ các nguồn chính thống uy tín: Trung tâm Dự báo KTTV Quốc gia, Báo Chính phủ, TTXVN... Loại bỏ tin giả, tin rác.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50">
              <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-xl flex items-center justify-center mb-4">
                <Zap className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Cập nhật tức thời</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                Hệ thống giám sát 24/7, phát hiện và cập nhật sự kiện thiên tai mới nhất chỉ trong vài phút sau khi được công bố, giúp người dùng nắm bắt thông tin nhanh nhất.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50">
              <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-xl flex items-center justify-center mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Độ tin cậy cao</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                Ứng dụng AI/NLP để chấm điểm tin cậy cho từng sự kiện. Các thông tin quan trọng được kiểm chứng chéo từ nhiều nguồn trước khi hiển thị.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/50">
              <div className="w-10 h-10 bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 rounded-xl flex items-center justify-center mb-4">
                <Users className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Cộng đồng tương hỗ</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                Kết nối người dân vùng thiên tai với các nguồn lực cứu trợ. Chức năng đóng góp hiện trường (Crowdsourcing) giúp chia sẻ thông tin thực tế nhanh chóng.
              </p>
            </div>
          </div>
        </div>

        {/* Footer of Card */}
        <div className="bg-slate-50 dark:bg-slate-950/30 p-8 border-t border-slate-100 dark:border-slate-800">
           <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-center md:text-left">
             <div>
               <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Đơn vị chủ quản</div>
               <div className="font-bold text-slate-900 dark:text-white">Viện Địa công nghệ và Môi trường</div>
             </div>
             <div>
               <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Liên hệ hợp tác</div>
               <div className="font-bold text-slate-900 dark:text-white">0981.484.828</div>
             </div>
           </div>
        </div>
      </div>
    </div>
  );
}
