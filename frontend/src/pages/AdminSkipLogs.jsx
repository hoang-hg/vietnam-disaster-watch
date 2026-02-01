import { useState, useEffect } from "react";
import { 
  getJson, 
  postJson, 
  patchJson,
  downloadBlob,
  API_BASE 
} from "../api";
import { 
  CheckCircle, 
  XCircle, 
  ExternalLink, 
  Search, 
  RefreshCw,
  AlertCircle,
  FileText,
  Clock,
  AlertTriangle,
  MapPin,
  LayoutDashboard,
  Download,
  History,
  Settings
} from "lucide-react";
import { VALID_PROVINCES } from "../provinces";
import { DISASTER_METADATA } from "../theme.js";
import Toast from "../components/Toast.jsx";
import ConfirmModal from "../components/ConfirmModal.jsx";
import Pagination from "../components/Pagination.jsx";

export default function AdminSkipLogs() {
  const [activeTab, setActiveTab] = useState("pending"); // "pending" | "skipped" | "reports" | "crawler"
  const [pendingItems, setPendingItems] = useState([]);
  const [skippedItems, setSkippedItems] = useState([]);
  const [rejectedItems, setRejectedItems] = useState([]);
  const [crowdReports, setCrowdReports] = useState([]);
  const [crawlerStatus, setCrawlerStatus] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingId, setProcessingId] = useState(null);
  const [isReclassifying, setIsReclassifying] = useState(null);
  const [toast, setToast] = useState({ isVisible: false, message: "", type: "success" });
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, id: null, action: null });
  const ITEMS_PER_PAGE = 50;

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    setPage(1); // Reset to first page when searching
  }, [debouncedSearch]);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [activeTab, page]);

  async function fetchData(signal = null) {
    setLoading(true);
    setError(null);
    try {
      const skip = (page - 1) * ITEMS_PER_PAGE;
      const searchParam = debouncedSearch ? `&q=${encodeURIComponent(debouncedSearch)}` : "";

      if (activeTab === "pending") {
        const data = await getJson(`/api/admin/pending-articles?skip=${skip}&limit=${ITEMS_PER_PAGE}${searchParam}`, { signal });
        setPendingItems(data || []);
      } else if (activeTab === "rejected") {
        const data = await getJson(`/api/admin/rejected-articles?skip=${skip}&limit=${ITEMS_PER_PAGE}${searchParam}`, { signal });
        setRejectedItems(data || []);
      } else if (activeTab === "reports") {
        const data = await getJson("/api/user/admin/crowdsource/pending", { signal });
        setCrowdReports(data || []);
      } else if (activeTab === "crawler") {
        const data = await getJson("/api/admin/crawler-status", { signal });
        setCrawlerStatus(data || []);
      } else {
        const data = await getJson(`/api/admin/skip-logs?skip=${skip}&limit=${ITEMS_PER_PAGE}${searchParam}`, { signal }); 
        setSkippedItems(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError("Không thể tải dữ liệu: " + (e.message || String(e)));
    } finally {
      setLoading(false);
    }
  }

  async function handleExportDaily() {
    const date = new Date().toISOString().split('T')[0];
    try {
        await downloadBlob(`/api/admin/export/daily?date=${date}`, `bao_cao_ngay_${date}.xlsx`);
    } catch (err) {
        setError("Lỗi tải báo cáo: " + err.message);
    }
  }

  async function handleReclassify(id, currentType) {
    setIsReclassifying({ id, currentType });
  }

  async function submitReclassification(correctedType) {
    if (!isReclassifying) return;
    setProcessingId(isReclassifying.id);
    try {
        await postJson("/api/admin/ai-feedback", {
            article_id: isReclassifying.id,
            corrected_type: correctedType,
            comment: "Manual admin reclassification"
        });
        showToast("Đã cập nhật phân loại và lưu Feedback cho AI!");
        
        // [OPTIMIZATION] Update local state instead of full refresh
        setPendingItems(prev => prev.map(item => 
          item.id === isReclassifying.id ? { ...item, disaster_type: correctedType } : item
        ));
    } catch (e) {
        setError(e.message);
    } finally {
        setProcessingId(null);
        setIsReclassifying(null);
    }
  }

  async function handleApprove(id) {
    setProcessingId(id);
    try {
      await postJson(`/api/admin/approve-article/${id}`, {});
      setPendingItems(prev => prev.filter(item => item.id !== id));
      showToast("Đã duyệt tin và cập nhật sự kiện thành công!");
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleApproveReport(id) {
    setProcessingId(id);
    try {
        await patchJson(`/api/user/admin/crowdsource/${id}/approve`, {});
        setCrowdReports(prev => prev.filter(r => r.id !== id));
        showToast("Đã duyệt báo cáo hiện trường!");
    } catch (e) {
        setError(e.message);
    } finally {
        setProcessingId(null);
    }
  }

  async function handleRejectReport(id) {
    setProcessingId(id);
    try {
        await patchJson(`/api/user/admin/crowdsource/${id}/reject`, {});
        setCrowdReports(prev => prev.filter(r => r.id !== id));
        showToast("Đã từ chối báo cáo hiện trường.");
    } catch (e) {
        setError(e.message);
    } finally {
        setProcessingId(null);
    }
  }

  async function handleReject(id) {
    setProcessingId(id);
    try {
      await postJson(`/api/admin/reject-article/${id}`, {});
      setPendingItems(prev => prev.filter(item => item.id !== id));
      showToast("Đã từ chối và đưa tin vào danh sách đen.");
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleUnreject(id) {
    setProcessingId(id);
    try {
      await postJson(`/api/admin/unreject-article/${id}`, {});
      setRejectedItems(prev => prev.filter(item => item.id !== id));
      showToast("Đã phục hồi bài báo về trạng thái nghi vấn.");
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleTriggerCrawl() {
    setLoading(true);
    try {
        await postJson("/api/admin/crawler/run", {});
        showToast("Đã kích hoạt Crawler chạy ngầm!");
        // Refresh status after a bit
        setTimeout(() => fetchData(), 2000);
    } catch (e) {
        setError("Lỗi kích hoạt Crawler: " + e.message);
    } finally {
        setLoading(false);
    }
  }

  async function handleRestartSystem() {
    setConfirmModal({ 
        isOpen: true, 
        id: 'system', 
        action: 'restart', 
        type: 'system' 
    });
  }

  async function executeRestart() {
    setLoading(true);
    try {
        await postJson("/api/admin/system/restart", {});
        showToast("Đang gửi lệnh khởi động lại...", "warning");
        setTimeout(() => window.location.reload(), 3000);
    } catch (e) {
        setError("Lỗi khởi động lại: " + e.message);
    } finally {
        setLoading(false);
    }
  }

  const handleActionClick = (id, action, type = "article") => {
    setConfirmModal({ isOpen: true, id, action, type });
  };

  const confirmAction = async () => {
    const { id, action, type } = confirmModal;
    setConfirmModal({ isOpen: false, id: null, action: null });
    
    if (type === "article") {
        if (action === "approve") await handleApprove(id);
        if (action === "reject") await handleReject(id);
    } else if (type === "report") {
        if (action === "approve") await handleApproveReport(id);
        if (action === "reject") await handleRejectReport(id);
    } else if (type === "system") {
        if (action === "restart") await executeRestart();
    }
  };

  function showToast(message, type = "success") {
    setToast({ isVisible: true, message, type });
  }

  return (
    <div className="admin-wrapper min-h-screen bg-transparent py-8 px-4 sm:px-6 lg:px-8 transition-colors duration-300" style={{ backgroundColor: 'transparent' }}>
      <div className="max-w-6xl mx-auto">
        {/* Header Section */}
        <div className="mb-8 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          <div className="flex items-center justify-between w-full xl:w-auto">
            <div>
              <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                <LayoutDashboard className={`w-8 h-8 text-[#2fa1b3]`} />
                QUẢN TRỊ HỆ THỐNG
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1 font-medium">Trung tâm điều hành & Giám sát dữ liệu</p>
            </div>
            
            <button 
              onClick={handleExportDaily}
              className="xl:hidden p-3 bg-[#2fa1b3] text-white rounded-xl shadow-lg shadow-[#2fa1b3]/20"
              title="Xuất báo cáo ngày"
            >
              <Download className="w-5 h-5" />
            </button>
          </div>
          
          <div className="flex flex-wrap bg-white dark:bg-slate-800 p-1 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => { setActiveTab("pending"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "pending" 
                ? "bg-[#2fa1b3] text-white shadow-lg shadow-[#2fa1b3]/20" 
                : "text-slate-500 dark:text-slate-400 hover:text-[#2fa1b3] hover:bg-slate-50 dark:hover:bg-slate-700"
              }`}
            >
              NGHI VẤN ({pendingItems.length})
            </button>
            <button
              onClick={() => { setActiveTab("reports"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "reports" 
                ? "bg-red-600 text-white shadow-lg shadow-red-500/20" 
                : "text-slate-500 dark:text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
              }`}
            >
              HIỆN TRƯỜNG ({crowdReports.length})
            </button>
            <button
              onClick={() => { setActiveTab("crawler"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2 ${
                activeTab === "crawler" 
                ? "bg-slate-800 dark:bg-slate-700 text-white shadow-lg" 
                : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-700"
              }`}
            >
              <Settings className="w-4 h-4" />
              CRAWLER
            </button>
            <button
              onClick={() => { setActiveTab("skipped"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "skipped" 
                ? "bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-white" 
                : "text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50"
              }`}
            >
              LỊCH SỬ (LOG)
            </button>
            <button
              onClick={() => { setActiveTab("rejected"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "rejected" 
                ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" 
                : "text-slate-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/10"
              }`}
            >
              ĐÃ BỎ QUA
            </button>
          </div>

          <button 
            onClick={handleExportDaily}
            className="hidden xl:flex items-center gap-2 px-6 py-2.5 bg-[#2fa1b3] text-white rounded-xl font-black text-xs uppercase tracking-widest hover:bg-[#258a9b] transition-all shadow-lg shadow-[#2fa1b3]/20"
          >
            <Download className="w-4 h-4" />
            XUẤT BÁO CÁO NGÀY
          </button>
        </div>

        {/* Search Bar - Premium Glassmorphism */}
        <div className="mb-8 relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className={`w-5 h-5 transition-colors duration-300 ${searchTerm ? 'text-[#2fa1b3]' : 'text-slate-400 group-focus-within:text-[#2fa1b3]'}`} />
            </div>
            <input 
                type="text"
                placeholder="Tìm kiếm tiêu đề, nội dung hoặc mã bài báo..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-md border border-slate-200 dark:border-slate-700 rounded-3xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-[#2fa1b3]/10 focus:border-[#2fa1b3]/50 transition-all shadow-lg shadow-slate-200/50 dark:shadow-none placeholder:text-slate-400 dark:text-white"
            />
            {loading && (
                <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                    <RefreshCw className="w-4 h-4 text-slate-400 animate-spin" />
                </div>
            )}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-center gap-3 text-red-700 dark:text-red-400 animate-shake">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="font-semibold text-sm">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="w-16 h-16 border-4 border-[#2fa1b3]/20 border-t-[#2fa1b3] rounded-full animate-spin mb-4"></div>
            <p className="text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest text-xs">Đang tải dữ liệu...</p>
          </div>
        )}

        {!loading && activeTab === "crawler" && (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm items-center justify-between">
                <div>
                    <h3 className="text-lg font-black text-slate-800 dark:text-white uppercase">Trạng thái vận hành</h3>
                    <p className="text-xs text-slate-400 dark:text-slate-500 font-medium tracking-tight">Điều khiển và giám sát tiến trình Crawler</p>
                </div>
                <div className="flex gap-3">
                    <button 
                        onClick={handleTriggerCrawl}
                        className="flex items-center gap-2 px-5 py-2.5 bg-[#2fa1b3] text-white rounded-xl font-black text-xs uppercase tracking-widest hover:bg-[#258a9b] transition-all shadow-lg shadow-[#2fa1b3]/20"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Cập nhật ngay
                    </button>
                    <button 
                        onClick={handleRestartSystem}
                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-800 dark:bg-slate-700 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:bg-slate-900 dark:hover:bg-slate-600 transition-all shadow-lg"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Restart Backend
                    </button>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-700/50 border-bottom border-slate-200 dark:border-slate-700">
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500">Nguồn tin</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500 text-center">Trạng thái</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500">Cập nhật lần cuối</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500 text-center">Tin mới</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500 text-center">Độ trễ</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 dark:text-slate-500">Chi tiết</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                  {crawlerStatus.map((s) => (
                    <tr key={s.source_name} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/50 transition-colors">
                      <td className="px-6 py-4 font-bold text-slate-700 dark:text-slate-200">{s.source_name}</td>
                      <td className="px-6 py-4">
                        <div className="flex justify-center">
                          {s.status === 'success' ? (
                            <span className="w-3 h-3 bg-green-500 rounded-full shadow-sm shadow-green-500/50" />
                          ) : s.status === 'warning' ? (
                            <span className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse shadow-sm shadow-yellow-500/50" />
                          ) : (
                            <span className="w-3 h-3 bg-red-500 rounded-full animate-ping shadow-sm shadow-red-500/50" />
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-slate-400">
                        {new Date(s.last_run_at).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-6 py-4 text-center font-bold text-slate-700 dark:text-slate-200">{s.articles_added}</td>
                      <td className="px-6 py-4 text-center text-xs font-bold text-slate-400 dark:text-slate-500">{s.latency_ms}ms</td>
                      <td className="px-6 py-4">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full uppercase ${
                          s.status === 'error' ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400' : 'bg-slate-50 dark:bg-slate-700/50 text-slate-400 dark:text-slate-400'
                        }`}>
                          {s.last_error || 'Ổn định'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

        {!loading && activeTab !== "crawler" && (activeTab === "pending" ? pendingItems : (activeTab === "reports" ? crowdReports : skippedItems)).length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-800 rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 shadow-sm text-center px-6">
            <div className="w-20 h-20 bg-slate-50 dark:bg-slate-700 rounded-full flex items-center justify-center mb-6">
              <FileText className="w-10 h-10 text-slate-300 dark:text-slate-500" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-white">Danh sách trống</h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mt-2">
              {activeTab === "pending" 
                ? "Không có tin tức nào trong hàng đợi nghi vấn." 
                : activeTab === "rejected"
                ? "Không có tin tức nào bị bỏ qua thủ công."
                : activeTab === "reports"
                ? "Không có báo cáo nào từ người dân cần duyệt."
                : "Không tìm thấy lịch sử tin tức bị bỏ qua (Logs)."}
            </p>
          </div>
        )}

        <div className="space-y-4">
          {activeTab === "reports" ? (
             crowdReports.map((report) => (
                <div key={report.id} className="group bg-white dark:bg-slate-800 rounded-2xl border-2 border-red-100 dark:border-red-900/30 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden">
                    <div className="p-5 flex flex-col sm:flex-row gap-5">
                         <div className="sm:w-24 flex-shrink-0 flex sm:flex-col items-center justify-center gap-2">
                            <div className="w-14 h-14 bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center border-2 border-red-200 dark:border-red-800">
                                <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <span className="px-2 py-1 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded text-[10px] font-black uppercase">REPORT</span>
                         </div>
                         
                         <div className="flex-grow">
                            <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 font-bold mb-2">
                                <Clock className="w-3.5 h-3.5" />
                                {report.created_at ? new Date(report.created_at).toLocaleString("vi-VN") : "—"}
                                <span className="mx-1">•</span>
                                <span className="text-red-500 uppercase flex items-center gap-1">
                                    <MapPin className="w-3 h-3" /> {report.province || "Không xác định"}
                                </span>
                            </div>
                            <p className="text-slate-800 dark:text-white font-bold mb-3">{report.description}</p>
                            
                            {report.image_url && (
                                <a href={report.image_url} target="_blank" rel="noopener noreferrer" className="inline-block mt-2 mb-3">
                                    <img src={report.image_url} alt="Field report" className="h-32 rounded-xl object-cover border border-slate-200 dark:border-slate-700 hover:scale-105 transition-transform" />
                                </a>
                            )}

                            <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold flex items-center gap-4">
                                <span>USER_ID: {report.user_id}</span>
                                <span>VỊ TRÍ: {report.lat != null ? report.lat.toFixed(4) : "—"}, {report.lon != null ? report.lon.toFixed(4) : "—"}</span>
                            </div>
                         </div>

                         <div className="flex sm:flex-col justify-center gap-2 sm:w-32 flex-shrink-0">
                            <button
                                onClick={() => handleApproveReport(report.id)}
                                disabled={processingId === report.id}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-xl font-bold text-sm hover:bg-red-700 transition-all active:scale-95 disabled:opacity-50"
                            >
                                {processingId === report.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                                DUYỆT
                            </button>
                            <button
                                onClick={() => handleRejectReport(report.id)}
                                disabled={processingId === report.id}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 text-slate-400 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-xl font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-600 transition-all active:scale-95 disabled:opacity-50"
                            >
                                {processingId === report.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                                LOẠI BỎ
                            </button>
                         </div>
                    </div>
                </div>
             ))
          ) : (activeTab === "pending" ? pendingItems : activeTab === "rejected" ? rejectedItems : skippedItems).map((article, idx) => (
            <div 
              key={(activeTab === "pending" || activeTab === "rejected") ? article.id : idx} 
              className="group bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-xl hover:border-[#2fa1b3]/30 dark:hover:border-[#2fa1b3]/30 transition-all duration-300 overflow-hidden"
            >
              <div className="p-5 flex flex-col sm:flex-row gap-5">
                {/* Score & Badge Column */}
                <div className="flex flex-row sm:flex-col items-center justify-center gap-2 sm:w-24 flex-shrink-0">
                  <div className={`w-14 h-14 rounded-full flex flex-col items-center justify-center border-2 ${
                    (article.score || article.diagnose?.score) >= 11 ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-600 dark:text-orange-400' : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400'
                  }`}>
                    <span className="text-lg font-black leading-none">{((article.score || article.diagnose?.score || 0)).toFixed(1)}</span>
                    <span className="text-[10px] font-bold uppercase tracking-tighter opacity-70">ĐIỂM</span>
                  </div>
                  <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded text-[10px] font-bold tracking-widest uppercase truncate max-w-full">
                    {article.domain || "WEB"}
                  </span>
                </div>

                {/* Content Column */}
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 font-bold mb-2">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(article.published_at || article.timestamp).toLocaleString("vi-VN")}
                    <span className="mx-1">•</span>
                    <span className="text-[#2fa1b3] uppercase">{article.source}</span>
                    <span className="mx-1">•</span>
                    <span 
                      className="px-2 py-0.5 rounded text-[10px] font-black uppercase text-white shadow-sm"
                      style={{ backgroundColor: DISASTER_METADATA[article.disaster_type || article.diagnose?.disaster_type]?.color || '#94a3b8' }}
                    >
                      {DISASTER_METADATA[article.disaster_type || article.diagnose?.disaster_type]?.label || (article.disaster_type || article.diagnose?.disaster_type || "Không xác định")}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-800 dark:text-white leading-tight mb-2 pr-4">{article.title}</h3>
                  <div className="flex items-center gap-4 text-xs">
                    <a 
                      href={article.url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400 font-bold hover:underline"
                    >
                      XEM BÀI GỐC <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                    {article.diagnose?.rule_matches && (
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(article.diagnose.rule_matches).map(rule => (
                          <span key={rule} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded text-[10px] font-medium">#{rule}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {article.summary && (
                    <p className="mt-3 text-sm text-slate-600 dark:text-slate-300 line-clamp-2 bg-slate-50 dark:bg-slate-700/30 p-2 rounded-lg italic">
                      "{article.summary}"
                    </p>
                  )}
                </div>

                {/* Actions Column */}
                {activeTab === "pending" && (
                  <div className="flex sm:flex-col justify-center gap-2 sm:w-32 flex-shrink-0">
                    <button
                      onClick={() => handleReclassify(article.id, article.disaster_type)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl font-bold text-sm hover:bg-slate-200 dark:hover:bg-slate-600 transition-all active:scale-95"
                    >
                      <RefreshCw className="w-4 h-4" />
                      PHÂN LOẠI LẠI
                    </button>
                    <button
                      onClick={() => handleApprove(article.id)}
                      disabled={processingId === article.id}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-xl font-bold text-sm hover:bg-green-700 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {processingId === article.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                      DUYỆT
                    </button>
                    <button
                      onClick={() => handleReject(article.id)}
                      disabled={processingId === article.id}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 text-red-600 dark:text-red-400 border-2 border-red-500 dark:border-red-600 rounded-xl font-bold text-sm hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {processingId === article.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                      BỎ QUA
                    </button>
                  </div>
                )}

                {activeTab === "rejected" && (
                  <div className="flex sm:flex-col justify-center gap-2 sm:w-32 flex-shrink-0">
                    <button
                      onClick={() => handleUnreject(article.id)}
                      disabled={processingId === article.id}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-700 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {processingId === article.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                      PHỤC HỒI
                    </button>
                    <div className="text-[10px] text-center font-bold text-slate-400 dark:text-slate-500 mt-2 px-1">
                      BỞI ADMIN #{article.moderated_by}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* Pagination Controls */}
        {(activeTab === "pending" || activeTab === "skipped" || activeTab === "rejected") && 
         (activeTab === "pending" ? pendingItems : activeTab === "rejected" ? rejectedItems : skippedItems).length > 0 && (
          <div className="mt-8 flex justify-center items-center gap-4">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              TRANG TRƯỚC
            </button>
            <span className="text-sm font-bold text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-800 px-3 py-1 rounded border border-slate-200 dark:border-slate-700 shadow-sm">
               Trang {page}
            </span>
            <button
               onClick={() => setPage(p => p + 1)}
               disabled={
                 (activeTab === "pending" ? pendingItems : skippedItems).length < ITEMS_PER_PAGE
               }
               className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
               TRANG TIẾP
            </button>
          </div>
        )}
      </div>

      {/* Reclassification Modal */}
      {isReclassifying && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[110] p-4">
            <div className="bg-white dark:bg-slate-800 rounded-3xl w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden border border-slate-200 dark:border-slate-700">
                <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center">
                    <h3 className="text-xl font-black text-slate-800 dark:text-white">PHÂN LOẠI LẠI AI</h3>
                    <button onClick={() => setIsReclassifying(null)} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                        <XCircle className="w-6 h-6" />
                    </button>
                </div>
                <div className="p-6">
                    <p className="text-xs font-bold text-slate-400 uppercase mb-4 tracking-widest">Chọn loại thiên tai chính xác:</p>
                    <div className="grid grid-cols-2 gap-2">
                        {Object.entries(DISASTER_METADATA)
                            .filter(([id]) => id !== 'community' && id !== 'unknown')
                            .map(([id, meta]) => (
                            <button
                                key={id}
                                onClick={() => submitReclassification(id)}
                                className={`px-4 py-3 rounded-xl border-2 transition-all font-bold text-sm text-left ${
                                    isReclassifying.currentType === id 
                                    ? "bg-slate-800 dark:bg-indigo-600 text-white border-slate-800 dark:border-indigo-600 shadow-lg" 
                                    : "border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-[#2fa1b3]/30 dark:hover:bg-slate-700"
                                }`}
                            >
                                {meta.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="p-6 bg-slate-50 dark:bg-slate-700/30 text-center">
                    <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase">Hành động này sẽ gửi Feedback trực tiếp để cải thiện AI</p>
                </div>
            </div>
        </div>
      )}

      {/* Modern Toast Notification */}
      <Toast 
        {...toast}
        onClose={() => setToast(prev => ({ ...prev, isVisible: false }))} 
      />

      <ConfirmModal 
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal({ isOpen: false, id: null, action: null })}
        onConfirm={confirmAction}
        title={confirmModal.action === "restart" ? "Khởi động lại Backend" : (confirmModal.action === "approve" ? "Xác nhận duyệt" : "Xác nhận loại bỏ")}
        message={confirmModal.action === "restart"
            ? "Bạn có chắc chắn muốn khởi động lại Backend? Hệ thống sẽ tạm ngưng trong vài giây (yêu cầu server chạy chế độ --reload)."
            : (confirmModal.action === "approve" 
                ? `Bạn có chắc chắn muốn DUYỆT ${confirmModal.type === "article" ? "tin tức" : "báo cáo"} này?`
                : `Bạn có chắc chắn muốn LOẠI BỎ ${confirmModal.type === "article" ? "tin tức" : "báo cáo"} này khỏi hàng đợi?`
              )
        }
        confirmLabel={confirmModal.action === "restart" ? "Khởi động lại ngay" : "Thực hiện"}
        variant={confirmModal.action === "restart" ? "warning" : "danger"}
      />
    </div>
  );
}
