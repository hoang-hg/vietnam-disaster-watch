import React, { useState } from 'react';
import { X, Camera, MapPin, Send, AlertTriangle, Loader2 } from 'lucide-react';
import { postJson } from '../api';

const PROVINCES = [
    "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên", "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh", "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình", "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế", "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa", "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp", "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
].sort();

export default function CrowdsourceModal({ isOpen, onClose, user }) {
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [formData, setFormData] = useState({
        name: user?.full_name || "",
        phone: "",
        address: "",
        province: "",
        description: "",
        image_url: "",
        lat: 0,
        lon: 0
    });

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await postJson("/api/user/crowdsource/submit", formData);
            setSuccess(true);
            setTimeout(() => {
                onClose();
                setSuccess(false);
                setFormData({ 
                    name: user?.full_name || "", 
                    phone: "", 
                    address: "", 
                    province: "", 
                    description: "", 
                    image_url: "", 
                    lat: 0, 
                    lon: 0 
                });
            }, 2000);
        } catch (err) {
            alert("Lỗi: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGetLocation = () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition((position) => {
                setFormData(prev => ({
                    ...prev,
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                }));
            }, (err) => {
                alert("Không thể lấy vị trí: " + err.message);
            });
        } else {
            alert("Trình duyệt không hỗ trợ Geolocation");
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-red-100 dark:bg-red-500/20 rounded-xl">
                            <AlertTriangle className="w-5 h-5 text-red-600" />
                        </div>
                        <h3 className="font-black text-slate-900 dark:text-white uppercase tracking-tight">Đóng góp báo cáo hiện trường</h3>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors">
                        <X className="w-5 h-5 text-slate-500" />
                    </button>
                </div>

                {success ? (
                    <div className="p-12 text-center">
                        <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Send className="w-8 h-8 text-emerald-600" />
                        </div>
                        <h4 className="text-xl font-black text-slate-900 dark:text-white mb-2">Gửi thành công!</h4>
                        <p className="text-slate-500 text-sm">Báo cáo của bạn đang chờ Admin duyệt trước khi hiển thị trên bản đồ.</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="p-6 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Họ tên của bạn</label>
                                <input 
                                    type="text"
                                    placeholder="Nguyễn Văn A"
                                    value={formData.name || ""}
                                    onChange={e => setFormData({...formData, name: e.target.value})}
                                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Số điện thoại</label>
                                <input 
                                    type="tel"
                                    placeholder="0987..."
                                    value={formData.phone || ""}
                                    onChange={e => setFormData({...formData, phone: e.target.value})}
                                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all"
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                             <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Tỉnh thành</label>
                             <select 
                                 required
                                 value={formData.province}
                                 onChange={e => setFormData({...formData, province: e.target.value})}
                                 className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all"
                             >
                                 <option value="">Chọn tỉnh thành...</option>
                                 {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                             </select>
                        </div>

                        <div className="space-y-1">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Địa chỉ cụ thể</label>
                            <input 
                                type="text"
                                placeholder="Số nhà, đường, thôn/xóm..."
                                value={formData.address || ""}
                                onChange={e => setFormData({...formData, address: e.target.value})}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all"
                            />
                        </div>

                        <div className="space-y-1">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Mô tả tình hình</label>
                            <textarea 
                                required
                                placeholder="Chỗ tôi đang ngập cao 1m, nước vẫn đang lên..."
                                value={formData.description}
                                onChange={e => setFormData({...formData, description: e.target.value})}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all min-h-[100px]"
                            />
                        </div>

                        <div className="space-y-1">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">URL Hình ảnh (Nếu có)</label>
                            <div className="flex gap-2">
                                <input 
                                    type="url"
                                    placeholder="https://imgur.com/..."
                                    value={formData.image_url}
                                    onChange={e => setFormData({...formData, image_url: e.target.value})}
                                    className="flex-1 px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-500/20 transition-all"
                                />
                                <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
                                    <Camera className="w-5 h-5 text-slate-400" />
                                </div>
                            </div>
                        </div>

                        <div className="pt-2">
                            <button 
                                type="button"
                                onClick={handleGetLocation}
                                className="w-full py-3 bg-blue-50 dark:bg-blue-500/10 text-blue-600 font-bold rounded-2xl text-sm flex items-center justify-center gap-2 hover:bg-blue-100 transition-all border border-blue-100 dark:border-blue-500/20"
                            >
                                <MapPin className="w-4 h-4" />
                                {formData.lat ? `Đã lấy tọa độ (${formData.lat.toFixed(4)}, ${formData.lon.toFixed(4)})` : "Lấy vị trí hiện tại của tôi"}
                            </button>
                            <p className="text-[9px] text-slate-400 mt-2 text-center uppercase font-bold tracking-tighter">Địa chỉ IP và tọa độ sẽ được gửi kèm để xác thực tin cậy</p>
                        </div>

                        <button 
                            disabled={loading}
                            className="w-full py-4 bg-red-600 text-white font-black rounded-2xl shadow-lg shadow-red-500/30 hover:bg-red-700 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 uppercase tracking-widest disabled:opacity-70"
                        >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Send className="w-4 h-4" /> Gửi báo cáo</>}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
