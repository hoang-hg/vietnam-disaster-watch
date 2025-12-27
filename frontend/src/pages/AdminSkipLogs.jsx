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
  Clock,
  AlertTriangle,
  MapPin,
  LayoutDashboard,
  Download,
  History,
  Settings
} from "lucide-react";

export default function AdminSkipLogs() {
  const [activeTab, setActiveTab] = useState("pending"); // "pending" | "skipped" | "reports" | "crawler"
  const [pendingItems, setPendingItems] = useState([]);
  const [skippedItems, setSkippedItems] = useState([]);
  const [crowdReports, setCrowdReports] = useState([]);
  const [crawlerStatus, setCrawlerStatus] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingId, setProcessingId] = useState(null);
  const [isReclassifying, setIsReclassifying] = useState(null);
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
      } else if (activeTab === "reports") {
        const data = await getJson("/api/user/admin/crowdsource/pending");
        setCrowdReports(data || []);
      } else if (activeTab === "crawler") {
        const data = await getJson("/api/admin/crawler-status");
        setCrawlerStatus(data || []);
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

  async function handleExportDaily() {
    const token = localStorage.getItem("access_token");
    const date = new Date().toISOString().split('T')[0];
    window.open(`${API_BASE}/api/admin/export/daily?date=${date}&token=${token}`, '_blank');
  }

  async function handleReclassify(id, currentType) {
    setIsReclassifying({ id, currentType });
  }

  async function submitReclassification(correctedType) {
    if (!isReclassifying) return;
    setProcessingId(isReclassifying.id);
    try {
        const { postJson } = await import('../api');
        await postJson("/api/admin/ai-feedback", {
            article_id: isReclassifying.id,
            corrected_type: correctedType,
            comment: "Manual admin reclassification"
        });
        showToast("Đã cập nhật phân loại và lưu Feedback cho AI!");
        fetchData(); // Refresh list
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

  async function handleApproveReport(id) {
    setProcessingId(id);
    try {
        const { patchJson } = await import('../api');
        await patchJson(`/api/user/admin/crowdsource/${id}/approve`);
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
        const { patchJson } = await import('../api');
        await patchJson(`/api/user/admin/crowdsource/${id}/reject`);
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
        <div className="mb-8 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          <div className="flex items-center justify-between w-full xl:w-auto">
            <div>
              <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
                <LayoutDashboard className={`w-8 h-8 text-[#2fa1b3]`} />
                QUẢN TRỊ HỆ THỐNG
              </h1>
              <p className="text-slate-500 mt-1 font-medium">Trung tâm điều hành & Giám sát dữ liệu</p>
            </div>
            
            <button 
              onClick={handleExportDaily}
              className="xl:hidden p-3 bg-[#2fa1b3] text-white rounded-xl shadow-lg shadow-[#2fa1b3]/20"
              title="Xuất báo cáo ngày"
            >
              <Download className="w-5 h-5" />
            </button>
          </div>
          
          <div className="flex flex-wrap bg-white p-1 rounded-2xl shadow-sm border border-slate-200">
            <button
              onClick={() => { setActiveTab("pending"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "pending" 
                ? "bg-[#2fa1b3] text-white shadow-lg shadow-[#2fa1b3]/20" 
                : "text-slate-500 hover:text-[#2fa1b3] hover:bg-slate-50"
              }`}
            >
              NGHI VẤN ({pendingItems.length})
            </button>
            <button
              onClick={() => { setActiveTab("reports"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "reports" 
                ? "bg-red-600 text-white shadow-lg shadow-red-500/20" 
                : "text-slate-500 hover:text-red-600 hover:bg-red-50"
              }`}
            >
              HIỆN TRƯỜNG ({crowdReports.length})
            </button>
            <button
              onClick={() => { setActiveTab("crawler"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2 ${
                activeTab === "crawler" 
                ? "bg-slate-800 text-white shadow-lg" 
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
              }`}
            >
              <Settings className="w-4 h-4" />
              CRAWLER
            </button>
            <button
              onClick={() => { setActiveTab("skipped"); setPage(1); }}
              className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                activeTab === "skipped" 
                ? "bg-slate-200 text-slate-700" 
                : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
              }`}
            >
              LỊCH SỬ
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

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700 animate-shake">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="font-semibold text-sm">{error}</p>
          </div>
        )}

        {loading && !pendingItems.length && !skippedItems.length && !crowdReports.length && !crawlerStatus.length && (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl border border-slate-200 shadow-sm">
            <div className="w-16 h-16 border-4 border-[#2fa1b3]/20 border-t-[#2fa1b3] rounded-full animate-spin mb-4"></div>
            <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Đang tải dữ liệu...</p>
          </div>
        )}

        {!loading && activeTab === "crawler" && (
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-bottom border-slate-200">
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400">Nguồn tin</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 text-center">Trạng thái</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400">Cập nhật lần cuối</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 text-center">Tin mới</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 text-center">Độ trễ</th>
                    <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400">Chi tiết</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {crawlerStatus.map((s) => (
                    <tr key={s.source_name} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 font-bold text-slate-700">{s.source_name}</td>
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
                      <td className="px-6 py-4 text-xs font-medium text-slate-500">
                        {new Date(s.last_run_at).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-6 py-4 text-center font-bold text-slate-700">{s.articles_added}</td>
                      <td className="px-6 py-4 text-center text-xs font-bold text-slate-400">{s.latency_ms}ms</td>
                      <td className="px-6 py-4">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full uppercase ${
                          s.status === 'error' ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-400'
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
        )}

        {!loading && activeTab !== "crawler" && (activeTab === "pending" ? pendingItems : (activeTab === "reports" ? crowdReports : skippedItems)).length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl border border-dashed border-slate-300 shadow-sm text-center px-6">
            <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
              <FileText className="w-10 h-10 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">Danh sách trống</h3>
            <p className="text-slate-500 max-w-sm mt-2">
              {activeTab === "pending" 
                ? "Không có tin tức nào trong hàng đợi nghi vấn." 
                : activeTab === "reports"
                ? "Không có báo cáo nào từ người dân cần duyệt."
                : "Không tìm thấy lịch sử tin tức bị bỏ qua."}
            </p>
          </div>
        )}

        <div className="space-y-4">
          {activeTab === "reports" ? (
             crowdReports.map((report) => (
                <div key={report.id} className="group bg-white rounded-2xl border-2 border-red-100 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden">
                    <div className="p-5 flex flex-col sm:flex-row gap-5">
                         <div className="sm:w-24 flex-shrink-0 flex sm:flex-col items-center justify-center gap-2">
                            <div className="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center border-2 border-red-200">
                                <AlertTriangle className="w-6 h-6 text-red-600" />
                            </div>
                            <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-[10px] font-black uppercase">REPORT</span>
                         </div>
                         
                         <div className="flex-grow">
                            <div className="flex items-center gap-2 text-xs text-slate-400 font-bold mb-2">
                                <Clock className="w-3.5 h-3.5" />
                                {new Date(report.created_at).toLocaleString("vi-VN")}
                                <span className="mx-1">•</span>
                                <span className="text-red-500 uppercase flex items-center gap-1">
                                    <MapPin className="w-3 h-3" /> {report.province || "Không xác định"}
                                </span>
                            </div>
                            <p className="text-slate-800 font-bold mb-3">{report.description}</p>
                            
                            {report.image_url && (
                                <a href={report.image_url} target="_blank" rel="noopener noreferrer" className="inline-block mt-2 mb-3">
                                    <img src={report.image_url} alt="Field report" className="h-32 rounded-xl object-cover border border-slate-200 hover:scale-105 transition-transform" />
                                </a>
                            )}

                            <div className="text-[10px] text-slate-400 font-bold flex items-center gap-4">
                                <span>USER_ID: {report.user_id}</span>
                                <span>VỊ TRÍ: {report.lat.toFixed(4)}, {report.lon.toFixed(4)}</span>
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
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white text-slate-400 border border-slate-200 rounded-xl font-bold text-sm hover:bg-slate-50 transition-all active:scale-95 disabled:opacity-50"
                            >
                                {processingId === report.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                                LOẠI BỎ
                            </button>
                         </div>
                    </div>
                </div>
             ))
          ) : (activeTab === "pending" ? pendingItems : skippedItems).map((article, idx) => (
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
                      onClick={() => handleReclassify(article.id, article.disaster_type)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-100 text-slate-600 rounded-xl font-bold text-sm hover:bg-slate-200 transition-all active:scale-95"
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

      {/* Reclassification Modal */}
      {isReclassifying && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[110] p-4">
            <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                    <h3 className="text-xl font-black text-slate-800">PHÂN LOẠI LẠI AI</h3>
                    <button onClick={() => setIsReclassifying(null)} className="p-2 text-slate-400 hover:text-slate-600">
                        <XCircle className="w-6 h-6" />
                    </button>
                </div>
                <div className="p-6">
                    <p className="text-xs font-bold text-slate-400 uppercase mb-4 tracking-widest">Chọn loại thiên tai chính xác:</p>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            {id: "storm", label: "Bão/Áp thấp"},
                            {id: "flood", label: "Lũ lụt/Ngập lụt"},
                            {id: "flash_flood", label: "Lũ quét"},
                            {id: "landslide", label: "Sạt lở đất"},
                            {id: "drought", label: "Hạn hán"},
                            {id: "salinity", label: "Xâm nhập mặn"},
                            {id: "extreme_weather", label: "Thời tiết cực đoan"},
                            {id: "wildfire", label: "Cháy rừng"},
                            {id: "earthquake", label: "Động đất"},
                            {id: "other", label: "Khác/Tổng hợp"}
                        ].map(type => (
                            <button
                                key={type.id}
                                onClick={() => submitReclassification(type.id)}
                                className={`px-4 py-3 rounded-xl border-2 transition-all font-bold text-sm text-left ${
                                    isReclassifying.currentType === type.id 
                                    ? "bg-slate-800 text-white border-slate-800 shadow-lg" 
                                    : "border-slate-100 text-slate-600 hover:border-[#2fa1b3]/30 hover:bg-slate-50"
                                }`}
                            >
                                {type.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="p-6 bg-slate-50 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase">Hành động này sẽ gửi Feedback trực tiếp để cải thiện AI</p>
                </div>
            </div>
        </div>
      )}

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
