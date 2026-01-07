import React, { useState, useEffect, useCallback } from 'react';
import { Phone, MapPin, Shield, Info, ExternalLink, Search, Plus, Edit2, Trash2, X, Save, Loader2, AlertTriangle, CheckCircle } from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import { getJson, postJson, putJson, deleteJson } from '../api';
import { VALID_PROVINCES } from '../provinces';
import Toast from '../components/Toast.jsx';
import ConfirmModal from '../components/ConfirmModal.jsx';

import { THEME_COLORS, getNationalHotlineStyle } from '../theme';
import NationalHotlineCard from '../components/rescue/NationalHotlineCard.jsx';
import HotlineGridItem from '../components/rescue/HotlineGridItem.jsx';
import HotlineFilterBar from '../components/rescue/HotlineFilterBar.jsx';
import HotlineEditModal from '../components/rescue/HotlineEditModal.jsx';

const ALL_PROVINCES = ["Toàn quốc", ...VALID_PROVINCES];

// Custom Hook for debouncing
function useDebounce(value, delay) {
    const [debouncedValue, setDebouncedValue] = useState(value);
    useEffect(() => {
        const handler = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(handler);
    }, [value, delay]);
    return debouncedValue;
}

export default function RescuePage() {
    const [hotlines, setHotlines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterProvince, setFilterProvince] = useState("Toàn quốc");
    const [searchTerm, setSearchTerm] = useState("");
    const debouncedSearch = useDebounce(searchTerm, 300);
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
        
        // setFilterProvince("Toàn quốc"); // Removed redundant set 
        fetchHotlines();
        return () => window.removeEventListener("storage", checkRole);
    }, []);

    // Reset pagination when filtering
    useEffect(() => {
        setCurrentPage(1);
    }, [filterProvince, debouncedSearch]);

    const fetchHotlines = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterProvince !== "Toàn quốc") params.append("province", filterProvince);
            if (debouncedSearch) params.append("q", debouncedSearch);
            params.append("limit", "1000"); // Safety limit

            const data = await getJson(`/api/user/rescue/hotlines?${params.toString()}`);
            setHotlines(data);
        } catch (err) {
            showToast("Không thể tải danh sách cứu hộ: " + err.message, "error");
        } finally {
            setLoading(false);
        }
    };

    const showToast = (message, type = 'success') => {
        setToast({ isVisible: true, message, type });
    };

    // Separate Data for display
    const nationalHotlines = hotlines.filter(h => h.province === "Toàn quốc");
    const otherHotlines = hotlines.filter(h => h.province !== "Toàn quốc");

    // Re-fetch when filters change (server-side)
    useEffect(() => {
        fetchHotlines();
    }, [filterProvince, debouncedSearch]);

    // Handle pagination on filtered set (only if still many items)
    const totalPages = Math.ceil(otherHotlines.length / ITEMS_per_PAGE);
    const displayedHotlines = otherHotlines.slice(
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
                <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center justify-center gap-3 uppercase">
                    <Shield className="w-8 h-8 text-red-600" /> Hồ sơ Cứu hộ Khẩn cấp
                </h1>
                <p className="text-slate-500 mt-2 font-medium">Lưu lại các số điện thoại này để sử dụng trong trường hợp cấp bách</p>
            </div>

            {/* National Hotlines (Editable) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                {nationalHotlines.map((item) => (
                    <NationalHotlineCard 
                        key={item.id}
                        item={item}
                        style={getNationalHotlineStyle(item.phone)}
                        isAdmin={isAdmin}
                        onEdit={handleEdit}
                        onDelete={confirmDelete}
                    />
                ))}
                
                {nationalHotlines.length === 0 && !loading && (
                     <div className="col-span-full text-center text-slate-400 py-4 italic">Chưa có dữ liệu hotlines quốc gia</div>
                )}
            </div>

            {/* Province Hotlines Section */}
            <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden min-h-[400px]">
                <HotlineFilterBar 
                    filterProvince={filterProvince}
                    setFilterProvince={setFilterProvince}
                    searchTerm={searchTerm}
                    setSearchTerm={setSearchTerm}
                    isAdmin={isAdmin}
                    onAdd={handleAdd}
                    allProvinces={ALL_PROVINCES}
                    totalCount={otherHotlines.length}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 divide-x divide-y divide-slate-50">
                    {loading ? (
                        <div className="col-span-full py-20 flex justify-center text-slate-400">
                            <Loader2 className="w-8 h-8 animate-spin" />
                        </div>
                    ) : displayedHotlines.length === 0 ? (
                        <div className="col-span-full py-12 text-center text-slate-400 italic">Không tìm thấy dữ liệu phù hợp</div>
                    ) : (
                        displayedHotlines.map((h) => (
                            <HotlineGridItem 
                                key={h.id}
                                item={h}
                                isAdmin={isAdmin}
                                onEdit={handleEdit}
                                onDelete={confirmDelete}
                            />
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
            <HotlineEditModal 
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSubmit={handleSubmit}
                formData={formData}
                setFormData={setFormData}
                isSaving={isSaving}
                isEdit={!!editItem}
                allProvinces={ALL_PROVINCES}
            />

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
