import { useState, useEffect } from "react";
import { getJson, patchJson, API_BASE } from "../api";
import { Check, X, FileDown, MapPin, Phone, User, Loader2 } from "lucide-react";

export default function AdminReports() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchReports = async () => {
        setLoading(true);
        try {
            const data = await getJson("/api/user/admin/crowdsource/pending");
            setReports(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchReports();
    }, []);

    const handleApprove = async (id) => {
        if (!confirm("Duyệt báo cáo này?")) return;
        try {
            await patchJson(`/api/user/admin/crowdsource/${id}/approve`, {});
            setReports(prev => prev.filter(r => r.id !== id));
        } catch (e) {
            alert(e.message);
        }
    };

    const handleReject = async (id) => {
        if (!confirm("Từ chối báo cáo này?")) return;
        try {
            await patchJson(`/api/user/admin/crowdsource/${id}/reject`, {});
            setReports(prev => prev.filter(r => r.id !== id));
        } catch (e) {
            alert(e.message);
        }
    };

    const handleExport = () => {
        const token = localStorage.getItem("access_token");
        // Using fetch with blob to handle auth header if needed, but for simple link click usually token is cookie or query param. 
        // Since my auth uses Bearer token, I cannot simply use window.location.href unless I put token in query param or use fetch & blob.
        // Let's use fetch & blob download strategy.
        
        fetch(`${API_BASE}/api/user/admin/crowdsource/export`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bao_cao_hien_truong_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(err => alert("Lỗi tải xuống: " + err.message));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                     <h1 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">
                        DUYỆT TIN HIỆN TRƯỜNG
                    </h1>
                    <p className="text-slate-500 text-sm">Quản lý các báo cáo đóng góp từ cộng đồng</p>
                </div>
                <button 
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 transition-colors shadow-sm"
                >
                    <FileDown className="w-4 h-4" />
                    Xuất Excel (CSV)
                </button>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-slate-500 uppercase font-bold text-xs">
                            <tr>
                                <th className="px-6 py-4">Người gửi</th>
                                <th className="px-6 py-4">Vị trí / Tỉnh thành</th>
                                <th className="px-6 py-4">Mô tả</th>
                                <th className="px-6 py-4">Thời gian</th>
                                <th className="px-6 py-4 text-right">Hành động</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {loading ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400">
                                        <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                                        Đang tải...
                                    </td>
                                </tr>
                            ) : reports.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400 font-medium">
                                        Không có báo cáo nào đang chờ duyệt.
                                    </td>
                                </tr>
                            ) : reports.map(r => (
                                <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4 align-top">
                                        <div className="flex flex-col gap-1">
                                            <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                                                <User className="w-3.5 h-3.5 text-slate-400" />
                                                {r.name || "Khách"}
                                            </span>
                                            {r.phone && (
                                                <span className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
                                                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                                                    {r.phone}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 align-top w-1/4">
                                        <div className="flex flex-col gap-1">
                                            <span className="font-bold text-blue-600 dark:text-blue-400">{r.province}</span>
                                            {r.address && <span className="text-xs text-slate-500">{r.address}</span>}
                                            <span className="text-[10px] text-slate-400 font-mono mt-1 flex items-center gap-1">
                                                <MapPin className="w-3 h-3" />
                                                {r.lat.toFixed(4)}, {r.lon.toFixed(4)}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 align-top w-1/3">
                                        <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{r.description}</p>
                                        {r.image_url && (
                                            <a href={r.image_url} target="_blank" rel="noreferrer" className="block mt-2">
                                                <img src={r.image_url} alt="Minh họa" className="h-20 w-auto rounded border border-slate-200 object-cover" />
                                            </a>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 align-top text-slate-500 whitespace-nowrap">
                                        {new Date(r.created_at).toLocaleString('vi-VN')}
                                    </td>
                                    <td className="px-6 py-4 align-top text-right space-x-2">
                                        <button 
                                            onClick={() => handleApprove(r.id)}
                                            className="p-2 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors"
                                            title="Duyệt"
                                        >
                                            <Check className="w-4 h-4" />
                                        </button>
                                        <button 
                                            onClick={() => handleReject(r.id)}
                                            className="p-2 bg-slate-100 text-slate-500 rounded-lg hover:bg-slate-200 transition-colors"
                                            title="Từ chối"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
