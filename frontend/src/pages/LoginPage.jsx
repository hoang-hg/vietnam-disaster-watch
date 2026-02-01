import React, { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, ArrowRight, Github, Loader2, AlertCircle, X } from "lucide-react";
import { login as apiLogin, resetPassword } from "../api";

function ResetPasswordForm({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ type: "", content: "" });

  const handleReset = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMsg({ type: "error", content: "Mật khẩu xác nhận không khớp" });
      return;
    }
    
    setLoading(true);
    setMsg({ type: "", content: "" });
    try {
      await resetPassword(email, newPassword, confirmPassword);
      setMsg({ type: "success", content: "Đặt lại mật khẩu thành công!" });
      setTimeout(() => {
        onSuccess?.();
      }, 2000);
    } catch (err) {
      setMsg({ type: "error", content: err.message || "Lỗi đặt lại mật khẩu" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleReset} className="space-y-4">
      {msg.content && (
        <div className={`p-3 rounded-xl text-sm border ${msg.type === "success" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-red-50 text-red-600 border-red-200"}`}>
           {msg.content}
        </div>
      )}
      
      <div>
        <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Email tài khoản</label>
        <input 
          type="email" 
          required 
          className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="admin@example.com"
        />
      </div>

      <div>
        <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Mật khẩu mới</label>
        <input 
          type="password" 
          required 
          className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]"
          value={newPassword}
          onChange={e => setNewPassword(e.target.value)}
          placeholder="••••••••"
        />
      </div>

       <div>
        <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Xác nhận mật khẩu</label>
        <input 
          type="password" 
          required 
          className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]"
          value={confirmPassword}
          onChange={e => setConfirmPassword(e.target.value)}
          placeholder="••••••••"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2.5 bg-[#2fa1b3] hover:bg-[#258a9b] text-white font-bold rounded-xl transition-colors disabled:opacity-70 flex justify-center items-center"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Xác nhận đổi mật khẩu"}
      </button>
    </form>
  );
}

import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const from = location.state?.from || (user?.role === "admin" ? "/admin/logs" : "/");

  // Redirect if already logged in
  React.useEffect(() => {
    if (user && user.role !== "guest") {
        navigate(user.role === "admin" ? "/admin/logs" : "/");
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    
    try {
        const data = await apiLogin(formData.email, formData.password);
        
        
        if (!data.user) {
             throw new Error("No user data received");
        }

        login(data.user, data.access_token);
        
        // Navigation will be handled by useEffect, or we can force it here
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        navigate(from, { replace: true });
    } catch (err) {
        setError(err.message);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white dark:bg-slate-900 p-10 rounded-2xl shadow-xl border border-slate-100 dark:border-slate-800">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Chào mừng trở lại
          </h2>
          <p className="mt-2 text-center text-sm text-slate-600 dark:text-slate-400">
            Hoặc{" "}
            <Link to="/register" className="font-medium text-[#2fa1b3] hover:text-[#258a9b] transition-colors">
              tạo tài khoản mới nếu chưa có
            </Link>
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl flex items-center gap-3 text-sm animate-shake">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
            </div>
          )}

          <div className="rounded-md space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="email"
                  required
                  className="appearance-none block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 placeholder-slate-400 text-slate-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-[#2fa1b3] focus:border-transparent transition-all sm:text-sm"
                  placeholder="name@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Mật khẩu</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  className="appearance-none block w-full pl-10 pr-10 py-3 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 placeholder-slate-400 text-slate-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-[#2fa1b3] focus:border-transparent transition-all sm:text-sm"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
                <div 
                  className="absolute inset-y-0 right-0 pr-3 flex items-center cursor-pointer"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-5 w-5 text-slate-400" /> : <Eye className="h-5 w-5 text-slate-400" />}
                </div>
              </div>
            </div>
          </div>


          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-[#2fa1b3] focus:ring-[#2fa1b3] border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-900 dark:text-slate-300">
                Ghi nhớ đăng nhập
              </label>
            </div>

            <div className="text-sm">
              <button 
                type="button" 
                onClick={() => setShowForgotModal(true)}
                className="font-medium text-[#2fa1b3] hover:text-[#258a9b]"
              >
                Quên mật khẩu?
              </button>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-[#2fa1b3] hover:bg-[#258a9b] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2fa1b3] transition-all transform hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    ĐANG XỬ LÝ...
                  </>
              ) : (
                  <>
                    ĐĂNG NHẬP
                    <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                  </>
              )}
            </button>
          </div>

        </form>

        {/* Forgot Password Modal */}
        {showForgotModal && (
          <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 animate-in fade-in duration-200"
            onClick={() => setShowForgotModal(false)}
          >
             <div 
               className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-sm w-full p-6 space-y-4 border border-slate-200 dark:border-slate-800"
               onClick={e => e.stopPropagation()}
             >
                <div className="flex items-center justify-between">
                   <h3 className="text-lg font-bold text-slate-900 dark:text-white">Đặt lại mật khẩu</h3>
                   <button onClick={() => setShowForgotModal(false)} className="text-slate-400 hover:text-slate-600">
                      <X className="w-5 h-5" />
                   </button>
                </div>
                
                <ResetPasswordForm onSuccess={() => setShowForgotModal(false)} />
             </div>
          </div>
        )}
      </div>
    </div>
  );
}
