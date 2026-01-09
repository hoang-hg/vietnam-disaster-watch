import React, { useState } from 'react';
import { X, Camera, MapPin, Send, AlertTriangle, Loader2, Upload, ImageIcon } from 'lucide-react';
import { postJson } from '../api';
import Toast from './Toast.jsx';

import { VALID_PROVINCES } from '../provinces';

const INITIAL_FORM_DATA = {
    name: "",
    phone: "",
    address: "",
    province: "",
    description: "",
    image_url: "",
    lat: null,
    lon: null
};

export default function CrowdsourceModal({ isOpen, onClose, user }) {
    const [loading, setLoading] = useState(false);
    const [locLoading, setLocLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [toast, setToast] = useState({ isVisible: false, message: "", type: "success" });
    const fileInputRef = React.useRef(null);
    const [formData, setFormData] = useState({
        ...INITIAL_FORM_DATA,
        name: user?.full_name || ""
    });

    // Sync name if user logins/logouts while modal is openable
    React.useEffect(() => {
        if (user?.full_name && !formData.name) {
            setFormData(prev => ({ ...prev, name: user.full_name }));
        }
    }, [user, formData.name]);

    // Automatically trigger location fetching on open
    React.useEffect(() => {
        if (isOpen) {
            handleGetLocation();
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Basic Validation
        if (!formData.description) return setToast({ isVisible: true, message: "Vui lòng nhập mô tả tình hình", type: "error" });
        if (!formData.province) return setToast({ isVisible: true, message: "Vui lòng chọn tỉnh thành", type: "error" });

        const controller = new AbortController();
        setLoading(true);
        try {
            await postJson("/api/user/crowdsource/submit", formData, { signal: controller.signal });
            if (controller.signal.aborted) return;
            setSuccess(true);
            setTimeout(() => {
                onClose();
                setSuccess(false);
                setFormData({ 
                    ...INITIAL_FORM_DATA, 
                    name: user?.full_name || "" 
                });
            }, 3000);
        } catch (err) {
            if (err.name === 'AbortError') return;
            setToast({ isVisible: true, message: "Lỗi: " + err.message, type: "error" });
        } finally {
            if (!controller.signal.aborted) setLoading(false);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Limit size ~5MB
        if (file.size > 5 * 1024 * 1024) {
            setToast({ isVisible: true, message: "Kích thước ảnh không được quá 5MB", type: "error" });
            return;
        }

        const reader = new FileReader();
        reader.onloadend = () => {
            setFormData(prev => ({ ...prev, image_url: reader.result }));
            setToast({ isVisible: true, message: "Đã đính kèm ảnh thành công", type: "success" });
        };
        reader.readAsDataURL(file);
    };

    const handleGetLocation = () => {
        if (navigator.geolocation) {
            setLocLoading(true);
            const options = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            };

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    setFormData(prev => ({
                        ...prev,
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    }));
                    setLocLoading(false);
                }, 
                (err) => {
                    setLocLoading(false);
                    let msg = "Không thể lấy vị trí tự động.";
                    if (err.code === 1) msg = "Vui lòng cho phép trình duyệt truy cập vị trí để báo cáo chính xác nhất.";
                    setToast({ isVisible: true, message: msg, type: "warning" });
                },
                options
            );
        } else {
            setToast({ isVisible: true, message: "Trình duyệt không hỗ trợ Geolocation", type: "error" });
        }
    };

    return (
        <div 
            className="fixed inset-0 z-[100] flex items-start md:items-center justify-center p-2 md:p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200 overflow-y-auto"
            onClick={onClose}
        >
            <div 
                className="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 my-auto"
                onClick={e => e.stopPropagation()}
            >
                <Toast 
                    {...toast} 
                    onClose={() => setToast(prev => ({ ...prev, isVisible: false }))} 
                />
                <div className="px-8 py-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900 sticky top-0 z-10">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-red-50 dark:bg-red-500/10 rounded-2xl">
                            <AlertTriangle className="w-6 h-6 text-red-500" />
                        </div>
                        <div>
                            <h2 className="text-xl font-black text-slate-800 dark:text-white leading-none mb-1 tracking-tight">ĐÓNG GÓP BÁO CÁO HIỆN TRƯỜNG</h2>
                            <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Cung cấp thông tin thực tế từ hiện trường thiên tai</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors group">
                        <X className="w-6 h-6 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200" />
                    </button>
                </div>

                <div className="max-h-[80vh] overflow-y-auto custom-scrollbar">
                    {success ? (
                        <div className="p-16 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="w-24 h-24 bg-emerald-50 dark:bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                                <Send className="w-12 h-12 text-emerald-500 animate-bounce" />
                            </div>
                            <h4 className="text-3xl font-black text-slate-800 dark:text-white mb-4">Gửi thành công!</h4>
                            <p className="text-slate-500 text-lg max-w-md mx-auto leading-relaxed">
                                Thông tin của bạn vô cùng quý giá. Đội ngũ kiểm duyệt sẽ xác minh và cập nhật lên bản đồ ngay lập tức.
                            </p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="p-8 space-y-8">
                            {/* Information Grid Container */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Left Column: Basic Info */}
                                <div className="space-y-6">
                                    <div className="grid grid-cols-1 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Người báo cáo</label>
                                            <input 
                                                type="text"
                                                placeholder="Họ và tên của bạn"
                                                value={formData.name || ""}
                                                onChange={e => setFormData({...formData, name: e.target.value})}
                                                className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-bold focus:outline-none focus:ring-4 focus:ring-red-500/10 focus:border-red-500/40 transition-all shadow-sm"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Số điện thoại liên lạc</label>
                                            <input 
                                                type="tel"
                                                placeholder="Số điện thoại cá nhân"
                                                value={formData.phone || ""}
                                                onChange={e => setFormData({...formData, phone: e.target.value})}
                                                className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-bold focus:outline-none focus:ring-4 focus:ring-red-500/10 focus:border-red-500/40 transition-all shadow-sm"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-6 pt-4 border-t border-slate-100 dark:border-slate-800/50">
                                        <div className="space-y-2">
                                            <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Tỉnh / Thành phố</label>
                                            <select 
                                                required
                                                value={formData.province}
                                                onChange={e => setFormData({...formData, province: e.target.value})}
                                                className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-bold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-4 focus:ring-red-500/10 transition-all appearance-none cursor-pointer shadow-sm"
                                            >
                                                <option value="">Chọn khu vực chịu ảnh hưởng...</option>
                                                {VALID_PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Địa chỉ / Vị trí cụ thể</label>
                                            <input 
                                                type="text"
                                                placeholder="Xã, Huyện, Thôn hoặc tên địa danh..."
                                                value={formData.address || ""}
                                                onChange={e => setFormData({...formData, address: e.target.value})}
                                                className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-bold focus:outline-none focus:ring-4 focus:ring-red-500/10 focus:border-red-500/40 transition-all shadow-sm"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column: Details & Assets */}
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Mô tả chi tiết tình hình</label>
                                        <textarea 
                                            required
                                            placeholder="Nêu rõ diễn biến thiên tai, mức độ thiệt hại (nếu có) và tình trạng giao thông..."
                                            value={formData.description}
                                            onChange={e => setFormData({...formData, description: e.target.value})}
                                            className="w-full px-5 py-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-red-500/10 focus:border-red-500/40 transition-all h-[142px] resize-none shadow-sm leading-relaxed"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Ảnh thực tế từ hiện trường</label>
                                        {formData.image_url ? (
                                            <div className="relative rounded-2xl overflow-hidden border-2 border-slate-200 dark:border-slate-700 bg-black aspect-video group shadow-xl">
                                                <img src={formData.image_url} alt="Preview" className="w-full h-full object-contain" />
                                                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-all flex items-center justify-center backdrop-blur-[2px]">
                                                    <button 
                                                        type="button"
                                                        onClick={() => setFormData(prev => ({ ...prev, image_url: "" }))}
                                                        className="p-4 bg-red-600 text-white rounded-full shadow-2xl hover:bg-red-700 active:scale-90 transition-all"
                                                    >
                                                        <X className="w-6 h-6" />
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <button 
                                                type="button"
                                                onClick={() => fileInputRef.current.click()}
                                                className="w-full h-[142px] border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl flex flex-col items-center justify-center gap-3 hover:bg-red-50/30 dark:hover:bg-red-500/5 hover:border-red-300 dark:hover:border-red-500/40 transition-all group overflow-hidden relative shadow-sm"
                                            >
                                                <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-2xl group-hover:bg-red-100/50 dark:group-hover:bg-red-500/20 transition-all group-hover:scale-110">
                                                    <Camera className="w-6 h-6 text-slate-400 group-hover:text-red-500" />
                                                </div>
                                                <div className="text-center">
                                                    <span className="block text-[11px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">Tải ảnh lên</span>
                                                    <span className="block text-[9px] text-slate-400 font-bold mt-1">(Dung lượng tối đa 5MB)</span>
                                                </div>
                                            </button>
                                        )}
                                        <input 
                                            type="file" 
                                            ref={fileInputRef}
                                            accept="image/*"
                                            onChange={handleFileChange}
                                            className="hidden"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Location Section - Full Width */}
                            <div className="pt-6 border-t border-slate-100 dark:border-slate-800/50">
                                <button 
                                    type="button"
                                    onClick={handleGetLocation}
                                    disabled={locLoading}
                                    className={`w-full py-5 px-6 rounded-2xl text-[13px] font-black flex items-center justify-center gap-4 transition-all shadow-md group ${
                                        formData.lat != null 
                                            ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 border-2 border-emerald-100 dark:border-emerald-500/20" 
                                            : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-2 border-slate-200 dark:border-slate-700 hover:bg-red-50 dark:hover:bg-red-500/10 hover:border-red-200 hover:text-red-500"
                                    } disabled:opacity-70`}
                                >
                                    {locLoading ? (
                                        <Loader2 className="w-5 h-5 animate-spin text-red-500" />
                                    ) : formData.lat != null ? (
                                        <MapPin className="w-5 h-5 fill-emerald-500 text-emerald-600 animate-pulse" />
                                    ) : (
                                        <MapPin className="w-5 h-5" />
                                    )}
                                    <div className="text-left">
                                        <span className="block uppercase tracking-wider leading-none mb-1">
                                            {locLoading ? "ĐANX XÁC ĐỊNH VỊ TRÍ..." : (formData.lat != null ? "VỊ TRÍ ĐÃ ĐƯỢC XÁC ĐỊNH" : "XÁC ĐỊNH TỌA ĐỘ HIỆN TẠI")}
                                        </span>
                                        <span className="block text-[10px] font-bold opacity-70 tracking-tight">
                                            {formData.lat != null ? `Tọa độ: ${formData.lat.toFixed(6)}, ${formData.lon.toFixed(6)}` : "Tăng độ chính xác và tin cậy cho báo cáo của bạn"}
                                        </span>
                                    </div>
                                </button>
                            </div>

                            {/* Main Action - Sticky Footer style within form */}
                            <div className="pt-4 pb-2">
                                <button 
                                    disabled={loading}
                                    className="w-full py-5 bg-gradient-to-r from-red-600 to-red-500 text-white font-black rounded-3xl shadow-2xl shadow-red-500/40 hover:shadow-red-500/60 active:scale-[0.98] transition-all flex items-center justify-center gap-4 uppercase tracking-[0.2em] text-sm disabled:opacity-70"
                                >
                                    {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <><Send className="w-6 h-6" /> Gửi báo cáo hiện trường</>}
                                </button>
                                <p className="text-center text-[10px] text-slate-400 font-bold mt-4 uppercase tracking-widest opacity-60">
                                    Thông tin của bạn sẽ được bảo mật và chỉ dùng cho mục đích cứu hộ
                                </p>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );

}
