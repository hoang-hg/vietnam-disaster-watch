import React, { useEffect, useState } from "react";
import { getJson, API_BASE } from "../api";
import { 
  CheckCircle, 
  XCircle, 
  ExternalLink, 
  Search, 
  RefreshCw,
  AlertCircle,
  FileText,
  Clock
} from "lucide-react";

export default function AdminSkipLogs() {
  const [activeTab, setActiveTab] = useState("pending"); // "pending" | "skipped"
  const [pendingItems, setPendingItems] = useState([]);
  const [skippedItems, setSkippedItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingId, setProcessingId] = useState(null);
  const [message, setMessage] = useState(null);
  const [page, setPage] = useState(1);
  const ITEMS_PER_PAGE = 50;

  useEffect(() => {
    fetchData();
  }, [activeTab, page]);

  async function fetchData() {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "pending") {
        const skip = (page - 1) * ITEMS_PER_PAGE;
        const data = await getJson(`/api/admin/pending-articles?skip=${skip}&limit=${ITEMS_PER_PAGE}`);
        setPendingItems(data || []);
      } else {
        const data = await getJson("/api/admin/skip-logs?limit=200");
        setSkippedItems(Array.isArray(data) ? data.reverse() : []);
      }
    } catch (e) {
      console.error(e);
      setError("Không thể tải dữ liệu: " + (e.message || String(e)));
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(id) {
    setProcessingId(id);
    try {
      const res = await fetch(`${API_BASE}/api/admin/approve-article/${id}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        }
      });
      if (!res.ok) throw new Error("Duyệt tin thất bại");
      setPendingItems(prev => prev.filter(item => item.id !== id));
      showToast("Đã duyệt tin và cập nhật sự kiện thành công!");
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(id) {
    setProcessingId(id);
    try {
      const res = await fetch(`${API_BASE}/api/admin/reject-article/${id}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        }
      });
      if (!res.ok) throw new Error("Từ chối tin thất bại");
      setPendingItems(prev => prev.filter(item => item.id !== id));
      showToast("Đã từ chối và đưa tin vào danh sách đen.");
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessingId(null);
    }
  }

  function showToast(msg) {
    setMessage(msg);
    setTimeout(() => setMessage(null), 3000);
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
              <RefreshCw className={`w-8 h-8 text-[#2fa1b3] ${loading ? 'animate-spin' : ''}`} />
              QUẢN LÝ & DUYỆT TIN TỨC
            </h1>
            <p className="text-slate-500 mt-1 font-medium">Hệ thống lọc 3 cấp: Tự động - Nghi vấn - Loại bỏ</p>
          </div>
          
          <div className="flex bg-white p-1 rounded-xl shadow-sm border border-slate-200">
            <button
              onClick={() => { setActiveTab("pending"); setPage(1); }}
              className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === "pending" 
                ? "bg-[#2fa1b3] text-white shadow-md shadow-[#2fa1b3]/20" 
                : "text-slate-500 hover:text-[#2fa1b3] hover:bg-slate-50"
              }`}
            >
              CHỜ DUYỆT ({pendingItems.length >= ITEMS_PER_PAGE ? `${ITEMS_PER_PAGE}+` : pendingItems.length})
            </button>
            <button
              onClick={() => { setActiveTab("skipped"); setPage(1); }}
              className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === "skipped" 
                ? "bg-[#2fa1b3] text-white shadow-md shadow-[#2fa1b3]/20" 
                : "text-slate-500 hover:text-[#2fa1b3] hover:bg-slate-50"
              }`}
            >
              LỊCH SỬ BỎ QUA
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700 animate-shake">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="font-semibold text-sm">{error}</p>
          </div>
        )}

        {loading && !pendingItems.length && !skippedItems.length && (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl border border-slate-200 shadow-sm">
            <div className="w-16 h-16 border-4 border-[#2fa1b3]/20 border-t-[#2fa1b3] rounded-full animate-spin mb-4"></div>
            <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Đang tải dữ liệu...</p>
          </div>
        )}

        {!loading && (activeTab === "pending" ? pendingItems : skippedItems).length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl border border-dashed border-slate-300 shadow-sm text-center px-6">
            <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
              <FileText className="w-10 h-10 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">Danh sách trống</h3>
            <p className="text-slate-500 max-w-sm mt-2">
              {activeTab === "pending" 
                ? "Không có tin tức nào trong hàng đợi nghi vấn. Hệ thống tự động đang làm việc rất tốt!" 
                : "Không tìm thấy lịch sử tin tức bị bỏ qua."}
            </p>
            <button 
              onClick={fetchData}
              className="mt-6 flex items-center gap-2 px-6 py-2 bg-slate-800 text-white rounded-full font-bold text-sm hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> LÀM MỚI
            </button>
          </div>
        )}

        <div className="space-y-4">
          {(activeTab === "pending" ? pendingItems : skippedItems).map((article, idx) => (
            <div 
              key={activeTab === "pending" ? article.id : idx} 
              className="group bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-xl hover:border-[#2fa1b3]/30 transition-all duration-300 overflow-hidden"
            >
              <div className="p-5 flex flex-col sm:flex-row gap-5">
                {/* Score & Badge Column */}
                <div className="flex flex-row sm:flex-col items-center justify-center gap-2 sm:w-24 flex-shrink-0">
                  <div className={`w-14 h-14 rounded-full flex flex-col items-center justify-center border-2 ${
                    (article.score || article.diagnose?.score) >= 11 ? 'bg-orange-50 border-orange-200 text-orange-600' : 'bg-blue-50 border-blue-200 text-blue-600'
                  }`}>
                    <span className="text-lg font-black leading-none">{((article.score || article.diagnose?.score || 0)).toFixed(1)}</span>
                    <span className="text-[10px] font-bold uppercase tracking-tighter opacity-70">ĐIỂM</span>
                  </div>
                  <span className="px-2 py-1 bg-slate-100 text-slate-500 rounded text-[10px] font-bold tracking-widest uppercase truncate max-w-full">
                    {article.domain || "WEB"}
                  </span>
                </div>

                {/* Content Column */}
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-bold mb-2">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(article.published_at || article.timestamp).toLocaleString("vi-VN")}
                    <span className="mx-1">•</span>
                    <span className="text-[#2fa1b3] uppercase">{article.source}</span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-800 leading-tight mb-2 pr-4">{article.title}</h3>
                  <div className="flex items-center gap-4 text-xs">
                    <a 
                      href={article.url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="flex items-center gap-1.5 text-blue-600 font-bold hover:underline"
                    >
                      XEM BÀI GỐC <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                    {article.diagnose?.rule_matches && (
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(article.diagnose.rule_matches).map(rule => (
                          <span key={rule} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-medium">#{rule}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {article.summary && (
                    <p className="mt-3 text-sm text-slate-600 line-clamp-2 bg-slate-50 p-2 rounded-lg italic">
                      "{article.summary}"
                    </p>
                  )}
                </div>

                {/* Actions Column */}
                {activeTab === "pending" && (
                  <div className="flex sm:flex-col justify-center gap-2 sm:w-32 flex-shrink-0">
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
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white text-red-600 border-2 border-red-500 rounded-xl font-bold text-sm hover:bg-red-50 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {processingId === article.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                      BỎ QUA
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* Pagination Controls */}
        {activeTab === "pending" && (pendingItems.length > 0 || page > 1) && (
          <div className="mt-8 flex justify-center items-center gap-4">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              TRANG TRƯỚC
            </button>
            <span className="text-sm font-bold text-slate-500 bg-white px-3 py-1 rounded border border-slate-200 shadow-sm">
               Trang {page}
            </span>
            <button
               onClick={() => setPage(p => p + 1)}
               disabled={pendingItems.length < ITEMS_PER_PAGE}
               className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
               TRANG TIẾP
            </button>
          </div>
        )}
      </div>

      {/* Modern Toast Notification */}
      {message && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-3 px-6 py-4 bg-slate-900/95 backdrop-blur-sm text-white rounded-2xl shadow-2xl border border-white/10 z-[100] animate-in slide-in-from-bottom-5 fade-in">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="font-bold text-sm tracking-wide">{message}</span>
        </div>
      )}
    </div>
  );
}
