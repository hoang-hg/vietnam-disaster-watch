import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield, FileText, Lock } from 'lucide-react';

export default function Terms() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 font-sans">
      <Link 
        to="/" 
        className="inline-flex items-center text-sm font-bold text-slate-500 hover:text-[#2fa1b3] mb-8 transition-colors group"
      >
        <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
        Quay lại trang chính
      </Link>

      <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="p-8 md:p-12 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-2xl flex items-center justify-center mb-6 text-blue-600 dark:text-blue-400">
            <FileText className="w-8 h-8" />
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white mb-4">Điều khoản sử dụng</h1>
          <p className="text-slate-600 dark:text-slate-400 text-lg leading-relaxed max-w-2xl">
            Các quy định và điều khoản khi sử dụng dịch vụ trên hệ thống Báo tổng hợp rủi ro thiên tai.
          </p>
        </div>

        <div className="p-8 md:p-12 space-y-10">
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-[#2fa1b3] rounded-full display-block"></span>
              1. Giới thiệu chung
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Chào mừng bạn đến với hệ thống <strong>Báo tổng hợp rủi ro thiên tai</strong>. Khi truy cập và sử dụng website này, bạn đồng ý tuân thủ các điều khoản được quy định dưới đây. Nếu bạn không đồng ý với bất kỳ điều khoản nào, vui lòng ngưng sử dụng dịch vụ.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-[#2fa1b3] rounded-full display-block"></span>
              2. Mục đích sử dụng thông tin
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Thông tin trên website mang tính chất tham khảo, tổng hợp từ các nguồn tin chính thống (Báo Chính phủ, TTXVN, KTTV Quốc gia...). Chúng tôi không chịu trách nhiệm về tính chính xác tuyệt đối của các tin tức được tự động tổng hợp, mặc dù hệ thống luôn nỗ lực kiểm duyệt tốt nhất có thể.
            </p>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Người dùng cần đối chiếu thông tin với các thông báo chính thức từ cơ quan chức năng địa phương trước khi đưa ra các quyết định quan trọng liên quan đến an toàn tính mạng và tài sản.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-[#2fa1b3] rounded-full display-block"></span>
              3. Quyền sở hữu trí tuệ
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Website thuộc quyền sở hữu của <strong>Viện Địa công nghệ và Môi trường</strong>. Mọi tài nguyên, mã nguồn, và cơ sở dữ liệu trên hệ thống đều thuộc bản quyền của đơn vị phát triển, ngoại trừ các nội dung tin tức được trích dẫn từ nguồn bên thứ ba.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-[#2fa1b3] rounded-full display-block"></span>
              4. Hành vi bị nghiêm cấm
            </h2>
            <ul className="list-disc pl-5 space-y-2 text-slate-600 dark:text-slate-400 leading-relaxed">
              <li>Sử dụng hệ thống để phát tán tin giả, gây hoang mang dư luận.</li>
              <li>Can thiệp, phá hoại hệ thống kỹ thuật của website.</li>
              <li>Thu thập dữ liệu người dùng trái phép.</li>
            </ul>
          </section>
        </div>
        
        <div className="bg-slate-50 dark:bg-slate-950/30 p-8 text-center border-t border-slate-100 dark:border-slate-800">
           <p className="text-slate-500 dark:text-slate-500 text-sm">
             Cập nhật lần cuối: 01/02/2026
           </p>
        </div>
      </div>
    </div>
  );
}
