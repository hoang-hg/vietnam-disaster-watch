import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Lock, ShieldCheck, Eye } from 'lucide-react';

export default function Privacy() {
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
          <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-900/20 rounded-2xl flex items-center justify-center mb-6 text-emerald-600 dark:text-emerald-400">
            <Lock className="w-8 h-8" />
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white mb-4">Chính sách bảo mật</h1>
          <p className="text-slate-600 dark:text-slate-400 text-lg leading-relaxed max-w-2xl">
            Cam kết bảo vệ thông tin cá nhân và dữ liệu của người dùng trên hệ thống Báo tổng hợp rủi ro thiên tai.
          </p>
        </div>

        <div className="p-8 md:p-12 space-y-10">
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-emerald-500 rounded-full display-block"></span>
              1. Thu thập thông tin
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Chúng tôi chỉ thu thập các thông tin cơ bản cần thiết để cải thiện trải nghiệm người dùng, bao gồm:
            </p>
            <ul className="list-disc pl-5 space-y-2 text-slate-600 dark:text-slate-400 leading-relaxed mt-2">
              <li>Thông tin tài khoản (Tên, Email) khi bạn đăng ký thành viên.</li>
              <li>Vị trí địa lý (nếu được cho phép) để gửi cảnh báo thiên tai phù hợp với khu vực của bạn.</li>
              <li>Tỉnh thành quan tâm (Favorite Province) để cá nhân hóa dòng tin tức.</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-emerald-500 rounded-full display-block"></span>
              2. Sử dụng thông tin
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Thông tin của bạn được sử dụng duy nhất cho các mục đích:
            </p>
            <ul className="list-disc pl-5 space-y-2 text-slate-600 dark:text-slate-400 leading-relaxed mt-2">
              <li>Cung cấp tin tức và cảnh báo thiên tai kịp thời.</li>
              <li>Hỗ trợ kỹ thuật và giải đáp thắc mắc người dùng.</li>
              <li>Phân tích thống kê ẩn danh để cải thiện chất lượng dịch vụ.</li>
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-emerald-500 rounded-full display-block"></span>
              3. Chia sẻ thông tin
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Chúng tôi cam kết <strong>tuyệt đối không chia sẻ, bán, hoặc tiết lộ</strong> thông tin cá nhân của người dùng cho bất kỳ bên thứ ba nào, trừ khi có yêu cầu bắt buộc từ cơ quan nhà nước có thẩm quyền theo quy định của pháp luật Việt Nam.
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-1.5 h-6 bg-emerald-500 rounded-full display-block"></span>
              4. Bảo mật dữ liệu
            </h2>
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              Hệ thống áp dụng các biện pháp kỹ thuật an ninh tiêu chuẩn để bảo vệ dữ liệu người dùng khỏi truy cập trái phép, mất mát hoặc phá hủy. Mật khẩu người dùng được mã hóa (hash) an toàn trong cơ sở dữ liệu.
            </p>
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
