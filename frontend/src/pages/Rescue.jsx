import React, { useState, useEffect, useCallback } from 'react';
import { Phone, MapPin, Shield, Info, ExternalLink, Search, Plus, Edit2, Trash2, X, Save, Loader2, AlertTriangle, CheckCircle } from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import { getJson, postJson, putJson, deleteJson } from '../api';
import { VALID_PROVINCES } from '../provinces';
import Toast from '../components/Toast.jsx';
import ConfirmModal from '../components/ConfirmModal.jsx';

const ALL_PROVINCES = ["Toàn quốc", ...VALID_PROVINCES];

// Helper to get style for national hotlines
const getNationalStyle = (phone) => {
    if (phone.includes("112")) return { color: "red", icon: Shield };
    if (phone.includes("113")) return { color: "blue", icon: Shield };
    if (phone.includes("114")) return { color: "orange", icon: Shield };
    if (phone.includes("115")) return { color: "emerald", icon: Shield };
    return { color: "slate", icon: Phone };
};


export default function RescuePage() {
    const [hotlines, setHotlines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterProvince, setFilterProvince] = useState("An Giang"); // Default to first alphabetic or intelligent default
    const [search, setSearch] = useState("");
    const [user, setUser] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    
    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editItem, setEditItem] = useState(null);
    const [formData, setFormData] = useState({ province: "", agency: "", phone: "", address: "" });

    // Toast & Confirm State
    const [toast, setToast] = useState({ isVisible: false, message: "", type: "success" });
    const [confirmModal, setConfirmModal] = useState({ isOpen: false, id: null });
    const [isDeleting, setIsDeleting] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    const ITEMS_per_PAGE = 12;

    useEffect(() => {
        const checkRole = () => {
            const u = localStorage.getItem("user");
            if (u) setUser(JSON.parse(u));
            else setUser(null);
        };
        checkRole();
        window.addEventListener("storage", checkRole);
        
        setFilterProvince("Toàn quốc"); 
        fetchHotlines();
        return () => window.removeEventListener("storage", checkRole);
    }, []);

    // Reset pagination when filtering
    useEffect(() => {
        setCurrentPage(1);
    }, [filterProvince, search]);

    const fetchHotlines = async () => {
        setLoading(true);
        try {
            const data = await getJson("/api/user/rescue/hotlines?limit=1000");
            setHotlines(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const showToast = (message, type = 'success') => {
        setToast({ isVisible: true, message, type });
    };

    // Separate Data
    const nationalHotlines = hotlines.filter(h => h.province === "Toàn quốc");
    const otherHotlines = hotlines.filter(h => h.province !== "Toàn quốc");

    const filteredHotlines = otherHotlines.filter(h => {
        const matchProvince = filterProvince === "Toàn quốc" || h.province === filterProvince;
        const matchSearch = h.province.toLowerCase().includes(search.toLowerCase()) || 
                            h.agency.toLowerCase().includes(search.toLowerCase()) ||
                            (h.address && h.address.toLowerCase().includes(search.toLowerCase()));
        return matchProvince && matchSearch;
    }).sort((a, b) => {
        // Sort by Province A-Z
        const provinceCompare = a.province.localeCompare(b.province);
        if (provinceCompare !== 0) return provinceCompare;
        // Then by Agency A-Z
        return a.agency.localeCompare(b.agency);
    });

    // Pagination
    const totalPages = Math.ceil(filteredHotlines.length / ITEMS_per_PAGE);
    const displayedHotlines = filteredHotlines.slice(
        (currentPage - 1) * ITEMS_per_PAGE,
        currentPage * ITEMS_per_PAGE
    );

    const handleEdit = (item) => {
        setEditItem(item);
        setFormData({
            province: item.province,
            agency: item.agency,
            phone: item.phone,
            address: item.address || ""
        });
        setIsModalOpen(true);
    };

    const handleAdd = () => {
        setEditItem(null);
        // Auto-select province if currently filtering by one
        const defaultProvince = filterProvince !== "Toàn quốc" ? filterProvince : "";
        setFormData({ province: defaultProvince, agency: "", phone: "", address: "" });
        setIsModalOpen(true);
    };

    const confirmDelete = (id) => {
        setConfirmModal({ isOpen: true, id });
    };

    const handleDelete = async () => {
        if (!confirmModal.id) return;
        setIsDeleting(true);
        try {
            await deleteJson(`/api/user/admin/rescue/${confirmModal.id}`);
            showToast("Đã xóa liên hệ thành công", "success");
            await fetchHotlines();
        } catch (err) {
            showToast(err.message || "Lỗi khi xóa", "error");
        } finally {
            setIsDeleting(false);
            setConfirmModal({ isOpen: false, id: null });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            if (editItem) {
                await putJson(`/api/user/admin/rescue/${editItem.id}`, formData);
                showToast("Cập nhật thành công", "success");
            } else {
                await postJson("/api/user/admin/rescue", formData);
                showToast("Thêm mới thành công", "success");
            }
            setIsModalOpen(false);
            fetchHotlines();
        } catch (err) {
            showToast(err.message || "Lỗi khi lưu", "error");
        } finally {
            setIsSaving(false);
        }
    };

    const isAdmin = user?.role === 'admin';

    return (
        <div className="max-w-6xl mx-auto px-4 py-8 relative">
            <Helmet>
                <title>Cứu hộ khẩn cấp | BÁO TỔNG HỢP RỦI RO THIÊN TAI</title>
                <meta name="description" content="Danh bạ số điện thoại cứu hộ, cứu nạn khẩn cấp khi có bão lũ, thiên tai tại các tỉnh thành Việt Nam." />
            </Helmet>

            {toast.isVisible && (
                <Toast 
                    message={toast.message} 
                    type={toast.type} 
                    isVisible={toast.isVisible}
                    onClose={() => setToast(prev => ({ ...prev, isVisible: false }))} 
                />
            )}
            
            <ConfirmModal 
                isOpen={confirmModal.isOpen} 
                title="Xác nhận xóa" 
                message="Bạn có chắc chắn muốn xóa thông tin liên hệ này không? Hành động này không thể hoàn tác."
                onConfirm={handleDelete}
                onClose={() => setConfirmModal({ isOpen: false, id: null })}
                confirmLabel={isDeleting ? "Đang xóa..." : "Xác nhận xóa"}
            />

            <div className="mb-8 text-center">
                <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center justify-center gap-3">
                    <Shield className="w-8 h-8 text-red-600" /> Hồ sơ Cứu hộ Khẩn cấp
                </h1>
                <p className="text-slate-500 mt-2 font-medium">Lưu lại các số điện thoại này để sử dụng trong trường hợp cấp bách</p>
            </div>

            {/* National Hotlines (Editable) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                {nationalHotlines.map((item) => {
                    const style = getNationalStyle(item.phone);
                    return (
                        <div key={item.id} className={`bg-white border-2 border-${style.color}-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all group relative`}>
                            {isAdmin && (
                                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => handleEdit(item)} className="p-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">
                                        <Edit2 className="w-3 h-3" />
                                    </button>
                                    <button onClick={() => confirmDelete(item.id)} className="p-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100">
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>
                            )}
                            <div className={`w-12 h-12 rounded-xl bg-${style.color}-50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                                <Phone className={`w-6 h-6 text-${style.color}-600`} />
                            </div>
                            <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{item.province}</div>
                            <div className={`text-3xl font-black text-${style.color}-600 my-1`}>{item.phone}</div>
                            <div className="text-xs font-semibold text-slate-600">{item.agency}</div>
                        </div>
                    );
                })}
                {/* Fallback if no national hotlines or if we want to show placeholder */}
                {nationalHotlines.length === 0 && !loading && (
                     <div className="col-span-full text-center text-slate-400 py-4 italic">Chưa có dữ liệu hotlines quốc gia</div>
                )}
            </div>

            {/* Province Hotlines Section */}
            <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex flex-col lg:flex-row justify-between items-center gap-4">
                    <h3 className="font-black text-slate-900 flex items-center gap-2 uppercase tracking-tight text-sm">
                        <MapPin className="w-4 h-4 text-blue-600" /> 
                        {filterProvince !== "Toàn quốc" ? `Đường dây nóng ${filterProvince}` : "Đường dây nóng các tỉnh thành"}
                        <span className="ml-1 text-slate-400 font-medium normal-case">({filteredHotlines.length} liên hệ)</span>
                    </h3>
                    
                    <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto items-center">
                        <div className="flex items-center gap-2 w-full sm:w-auto">
                            {/* Province Filter */}
                            <select 
                                value={filterProvince}
                                onChange={(e) => { setFilterProvince(e.target.value); setCurrentPage(1); }}
                                className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-full sm:w-auto"
                            >
                                {ALL_PROVINCES.map(p => (
                                    <option key={p} value={p}>{p}</option>
                                ))}
                            </select>
                            
                            {/* Reset Button */}
                            {filterProvince !== "Toàn quốc" && (
                                <button 
                                    onClick={() => { setFilterProvince("Toàn quốc"); setCurrentPage(1); }}
                                    className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-500 rounded-xl transition-colors"
                                    title="Xem tất cả"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            )}
                        </div>

                        {/* Search */}
                        <div className="relative w-full sm:w-64">
                             <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                             <input 
                                type="text" 
                                placeholder="Tìm theo tên cơ quan, địa chỉ..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
                             />
                        </div>

                        {/* Add Button (Admin) */}
                        {isAdmin && (
                            <button 
                                onClick={handleAdd}
                                className="px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-green-700 transition-colors shadow-sm whitespace-nowrap"
                            >
                                <Plus className="w-4 h-4" /> Thêm
                            </button>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 divide-x divide-y divide-slate-50">
                    {loading ? (
                        <div className="col-span-full py-20 flex justify-center text-slate-400">
                            <Loader2 className="w-8 h-8 animate-spin" />
                        </div>
                    ) : displayedHotlines.length === 0 ? (
                        <div className="col-span-full py-12 text-center text-slate-400 italic">Không tìm thấy dữ liệu phù hợp</div>
                    ) : (
                        displayedHotlines.map((h) => (
                            <div key={h.id} className="p-4 hover:bg-slate-50 transition-colors flex justify-between items-start group/item relative">
                                <div className="flex-1 min-w-0 pr-4">
                                    <div className="font-bold text-slate-900 text-sm truncate">{h.province}</div>
                                    <div className="text-[10px] text-slate-400 uppercase font-black truncate">{h.agency}</div>
                                    {h.address && (
                                        <div className="mt-1 text-xs text-slate-500 line-clamp-2">
                                            <MapPin className="w-3 h-3 inline mr-1 text-slate-400" />
                                            {h.address}
                                        </div>
                                    )}
                                </div>
                                <div className="flex flex-col items-end gap-2">
                                    <div 
                                        className="flex items-center gap-2 text-blue-600 font-black text-sm"
                                    >
                                        {h.phone}
                                        <Phone className="w-3.5 h-3.5" />
                                    </div>
                                    {isAdmin && (
                                        <div className="flex gap-1 pt-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                                            <button onClick={() => handleEdit(h)} className="p-1.5 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200">
                                                <Edit2 className="w-3 h-3" />
                                            </button>
                                            <button onClick={() => confirmDelete(h.id)} className="p-1.5 bg-red-100 text-red-600 rounded-lg hover:bg-red-200">
                                                <Trash2 className="w-3 h-3" />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
                
                {/* Pagination */}
                {!loading && totalPages > 1 && (
                    <div className="p-4 border-t border-slate-100 flex justify-center gap-2">
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                            <button
                                key={p}
                                onClick={() => setCurrentPage(p)}
                                className={`w-8 h-8 rounded-lg text-sm font-bold transition-all ${
                                    currentPage === p 
                                        ? "bg-blue-600 text-white shadow-md shadow-blue-500/20" 
                                        : "bg-slate-50 text-slate-500 hover:bg-slate-100"
                                }`}
                            >
                                {p}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <h3 className="font-bold text-slate-800">
                                {editItem ? "Chỉnh sửa liên hệ" : "Thêm liên hệ mới"}
                            </h3>
                            <button onClick={() => setIsModalOpen(false)} className="p-1 text-slate-400 hover:text-slate-600" disabled={isSaving}>
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Tỉnh thành</label>
                                <select 
                                    required
                                    disabled={isSaving}
                                    value={formData.province}
                                    onChange={e => setFormData({...formData, province: e.target.value})}
                                    className="w-full px-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-100"
                                >
                                    <option value="">Chọn tỉnh thành...</option>
                                    {ALL_PROVINCES.map(p => (
                                        <option key={p} value={p}>{p}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Tên đơn vị</label>
                                <input 
                                    required
                                    disabled={isSaving}
                                    type="text"
                                    placeholder="VD: Ban CM PCTT & TKCN"
                                    value={formData.agency}
                                    onChange={e => setFormData({...formData, agency: e.target.value})}
                                    className="w-full px-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-100"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Số điện thoại</label>
                                <input 
                                    required
                                    disabled={isSaving}
                                    type="text"
                                    placeholder="VD: 0243.3824.507"
                                    value={formData.phone}
                                    onChange={e => setFormData({...formData, phone: e.target.value})}
                                    className="w-full px-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-100"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Địa chỉ cụ thể</label>
                                <input 
                                    type="text"
                                    disabled={isSaving}
                                    placeholder="VD: 123 Đường ABC..."
                                    value={formData.address}
                                    onChange={e => setFormData({...formData, address: e.target.value})}
                                    className="w-full px-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-100"
                                />
                            </div>
                            <div className="pt-2">
                                <button 
                                    type="submit"
                                    disabled={isSaving}
                                    className="w-full py-3 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all flex justify-center gap-2 disabled:opacity-50"
                                >
                                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                    {isSaving ? "Đang lưu..." : "Lưu thông tin"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <div className="mt-12 text-center">
                 <div className="inline-flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-4">
                    BÁO TỔNG HỢP RỦI RO THIÊN TAI • Vì một Việt Nam an toàn hơn
                 </div>
                 <div className="flex justify-center gap-6">
                    <a href="#" className="text-slate-400 hover:text-blue-600 transition-colors text-xs font-bold flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" /> Website Chính phủ
                    </a>
                </div>
            </div>
        </div>
    );
}
