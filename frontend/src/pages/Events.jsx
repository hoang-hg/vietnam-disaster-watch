import { useEffect, useState, useMemo } from "react";
import {
  getJson,
  deleteJson,
  fmtType,
  downloadBlob
} from "../api.js";
import Pagination from "../components/Pagination.jsx";
import { THEME_COLORS, DISASTER_METADATA } from "../theme.js";
import { Trash2, Printer, Download, Loader2 } from "lucide-react";
import ConfirmModal from "../components/ConfirmModal.jsx";
import Toast from "../components/Toast.jsx";
import { VALID_PROVINCES } from "../provinces.js";
import { useLocation, useNavigate, useSearchParams, Link } from "react-router-dom";
import EventCard from "../components/events/EventCard.jsx";
import EventCardSkeleton from "../components/events/EventCardSkeleton.jsx";
import DateFilter from "../components/DateFilter.jsx";

// Local TYPE_TONES removed


import useDebounce from "../hooks/useDebounce";

import { useAuth } from "../contexts/AuthContext";

// ... existing imports

export default function Events() {
  const { user, isAdmin } = useAuth();
  const [showExportView, setShowExportView] = useState(false);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Filters (init from URL)
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [type, setType] = useState(searchParams.get("type") || "");
  const [province, setProvince] = useState(searchParams.get("province") || "");
  
  const [startDate, setStartDate] = useState(() => {
      const urlDate = searchParams.get("start_date");
      if (urlDate) return urlDate;
      // [FIX] Use local time for 'today', not UTC
      const d = new Date();
      const offset = d.getTimezoneOffset() * 60000;
      return (new Date(d - offset)).toISOString().split('T')[0];
  });
  
  const [endDate, setEndDate] = useState(searchParams.get("end_date") || "");
  
  // [OPTIMIZATION] Debounce search input
  const debouncedQ = useDebounce(q, 400);

  // Pagination
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get("page")) || 1);
  const itemsPerPage = 20; 
  const [totalEvents, setTotalEvents] = useState(0);
  
  const [error, setError] = useState(null);
  
  
  const [exportYear, setExportYear] = useState(new Date().getFullYear());
  const [exportMonth, setExportMonth] = useState(new Date().getMonth() + 1);

  // Modal states
  const [deleteId, setDeleteId] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExportingSummary, setIsExportingSummary] = useState(false);
  const [isExportingMonthly, setIsExportingMonthly] = useState(false);
  // Alias for spinner
  const isExporting = isExportingSummary || isExportingMonthly;

  // Toast state
  const [toast, setToast] = useState({ isVisible: false, message: '', type: 'success' });
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // Check for toast in URL
    const params = new URLSearchParams(location.search);
    if (params.get('deleted')) {
      setToast({ isVisible: true, message: 'Đã xóa sự kiện thành công!', type: 'success' });
      // Remove the param from URL without refreshing
      navigate(location.pathname, { replace: true });
    }
  }, []);

  const handleDelete = (e, eventId) => {
    e.preventDefault(); // Prevent navigation
    e.stopPropagation(); // Stop event from bubbling to parent <a> tag
    setDeleteId(eventId);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    setIsDeleting(true);
    try {
      await deleteJson(`/api/events/${deleteId}`);
      // Remove from local state immediately
      setEvents(prev => prev.filter(ev => ev.id !== deleteId));
      setTotalEvents(prev => Math.max(0, prev - 1));
      setDeleteId(null);
      setToast({ isVisible: true, message: 'Đã xóa sự kiện thành công!', type: 'success' });
    } catch (err) {
      if (err.message.includes("404") || err.status === 404) {
        // If already deleted, treat as success
        setEvents(prev => prev.filter(ev => ev.id !== deleteId));
        setDeleteId(null);
        setToast({ isVisible: true, message: 'Sự kiện đã được xóa trước đó.', type: 'info' });
      } else {
        setToast({ isVisible: true, message: "Xóa thất bại: " + err.message, type: 'error' });
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ isVisible: true, message, type });
  };

  const handleExportCSV = async () => {
    setIsExportingSummary(true);
    // [LOGIC REFINEMENT] Use fetch binary download to keep token in headers (more secure than URL)
    const token = localStorage.getItem("access_token");
    let query = ""; // Token passed via headers
    
    if (startDate && endDate) {
        query += `?start_date=${startDate}&end_date=${endDate}`;
    } else if (startDate) {
        query += `?start_date=${startDate}`;
    } else {
        query += "?";
    }
    
    if (q) query += `&q=${encodeURIComponent(q)}`;
    if (type) query += `&type=${type}`;
    if (province) query += `&province=${province}`;
    
    try {
        await downloadBlob(`/api/admin/export/summary${query}`, `thong_ke_thien_tai_${new Date().toISOString().split('T')[0]}.xlsx`);
        setToast({ isVisible: true, message: "Tải xuống thành công", type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Lỗi tải xuống: " + err.message, type: 'error' });
    } finally {
        setIsExportingSummary(false);
    }
  };

  const handleExportMonthly = async () => {
    setIsExportingMonthly(true);
    let query = `?month=${exportMonth}&year=${exportYear}`;
    if (type) query += `&type=${type}`;
    if (province) query += `&province=${province}`;

    try {
        await downloadBlob(`/api/admin/export/summary${query}`, `bao_cao_thang_${exportMonth}_${exportYear}.xlsx`);
        setToast({ isVisible: true, message: "Tải xuống báo cáo tháng thành công", type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Lỗi tải xuống: " + err.message, type: 'error' });
    } finally {
        setIsExportingMonthly(false);
    }
  };


  const fetchEvents = async (isBackground = false, pageToFetch = 1, signal = null) => {
    try {
      // 1. Generate Cache Key based on current params
      const cacheKey = `events_cache_${pageToFetch}_${type}_${province}_${debouncedQ}_${startDate}_${endDate}`;
      
      // 2. Try Instant Cache Load (SWR Strategy)
      if (!isBackground) {
          const cachedRaw = sessionStorage.getItem(cacheKey);
          if (cachedRaw) {
              const cachedData = JSON.parse(cachedRaw);
              // Only use cache if it's less than 5 minutes old
              if (Date.now() - cachedData.timestamp < 5 * 60 * 1000) {
                  setEvents(cachedData.items);
                  if (cachedData.total) setTotalEvents(cachedData.total);
                  setLoading(false); // Immediate user feedback
                  isBackground = true; // Switch to background mode for freshness check
              }
          }
      }
    
      if (!isBackground) setLoading(true);
      setError(null);
      
      const offset = (pageToFetch - 1) * itemsPerPage;
      const params = new URLSearchParams();
      params.append("limit", itemsPerPage.toString()); 
      params.append("offset", offset.toString());
      params.append("sort", "latest");
      params.append("wrapper", "true"); // Request total count
      
      if (type) params.append("type", type);
      if (province) params.append("province", province);
      if (debouncedQ) params.append("q", debouncedQ);
      
      if (startDate && endDate) {
          params.append("start_date", startDate);
          params.append("end_date", endDate);
      } else if (startDate) {
          params.append("start_date", startDate);
      }
      
      const response = await getJson(`/api/events?${params.toString()}`, { signal });
      if (signal?.aborted) return;
      
      let fetchedEvents = [];
      let totalCount = 0;
      
      if (response && response.items) {
          fetchedEvents = response.items;
          totalCount = response.total || 0;
          if (response.total !== undefined) {
              setTotalEvents(response.total);
          }
      } else if (Array.isArray(response)) {
           fetchedEvents = response;
      }
      
      // Update State
      setEvents(fetchedEvents);
      setCurrentPage(pageToFetch);
      
      // 3. Save to Session Cache for next time
      try {
        sessionStorage.setItem(cacheKey, JSON.stringify({
            items: fetchedEvents,
            total: totalCount,
            timestamp: Date.now()
        }));
      } catch (e) {
        // Quota exceeded or disabled
        console.warn("Cache save failed", e);
      }
      
    } catch (e) {
      if (e.name === 'AbortError') return;
      // Only show toast if not a "silent" background update
      if (!isBackground) {
          showToast(`Không thể tải danh sách sự kiện: ${e.message}`, "error");
          setError(e.message || "Load failed");
      }
    } finally {
      if (!isBackground) setLoading(false);
    }
  };

  // Handler for page change
  const handlePageChange = (newPage) => {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Initial load & Filter change & Page change
  useEffect(() => {
    const controller = new AbortController();
    fetchEvents(false, currentPage, controller.signal);
    
    // [FIX] More robust URL synchronization
    const newParams = {};
    if (debouncedQ) newParams.q = debouncedQ; 
    if (type) newParams.type = type;
    if (province) newParams.province = province;
    if (startDate) newParams.start_date = startDate;
    if (endDate) newParams.end_date = endDate;
    if (currentPage > 1) newParams.page = currentPage;
    
    const currentParams = Object.fromEntries(searchParams.entries());
    
    // Helper to compare current vs new
    const keys1 = Object.keys(newParams);
    const keys2 = Object.keys(currentParams);
    const isDifferent = keys1.length !== keys2.length || keys1.some(k => String(newParams[k]) !== String(currentParams[k]));
    
    if (isDifferent) {
        setSearchParams(newParams, { replace: true });
    }

    return () => controller.abort();
  }, [debouncedQ, type, province, startDate, endDate, currentPage]);

  // Handle URL changes (Back button)
  useEffect(() => {
    const urlQ = searchParams.get("q") || "";
    const urlType = searchParams.get("type") || "";
    const urlProv = searchParams.get("province") || "";
    const urlStart = searchParams.get("start_date") || new Date().toISOString().split('T')[0];
    const urlEnd = searchParams.get("end_date") || "";
    const urlPage = parseInt(searchParams.get("page")) || 1;

    if (urlQ !== q) setQ(urlQ);
    if (urlType !== type) setType(urlType);
    if (urlProv !== province) setProvince(urlProv);
    if (urlStart !== startDate) setStartDate(urlStart);
    if (urlEnd !== endDate) setEndDate(urlEnd);
    if (urlPage !== currentPage) setCurrentPage(urlPage);
  }, [searchParams]);

  // Auto-refresh every 5 minutes (only updates standard list if on page 1)
  useEffect(() => {
    const controller = new AbortController();
    
    // [REAL-TIME] Listen for global refresh signals from WebSocket (via MainLayout)
    const handleRefresh = () => {
        if (currentPage === 1) {
            fetchEvents(true, 1); // Background refresh for page 1
        }
    };
    window.addEventListener("news:update", handleRefresh);

    const interval = setInterval(() => {
      if (currentPage === 1) {
          fetchEvents(true, 1, controller.signal);
      }
    }, 300000); 
    return () => {
      controller.abort();
      clearInterval(interval);
      window.removeEventListener("news:update", handleRefresh);
    };
  }, [debouncedQ, type, province, startDate, endDate, currentPage]);

  const clearFilters = () => {
    setQ("");
    setType("");
    setProvince("");
    setStartDate("");
    setEndDate("");
    setCurrentPage(1);
    // fetchEvents will be triggered by useEffect
  };
  // No client-side pagination logic
  // const totalPages = Math.ceil(events.length / itemsPerPage);

  // Group events by date for rendering
  const groupedEvents = useMemo(() => {
    // No slicing, use all fetched events
    const currentEvents = events;
    
    const groups = {};
    const todayStr = new Date().toLocaleDateString('vi-VN');
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toLocaleDateString('vi-VN');

    currentEvents.forEach(e => {
        const d = new Date(e.started_at);
        const dateStr = d.toLocaleDateString('vi-VN');
        let label = dateStr;
        if (dateStr === todayStr) label = "Hôm nay";
        else if (dateStr === yesterdayStr) label = "Hôm qua";
        
        if (!groups[label]) groups[label] = [];
        groups[label].push(e);
    });
    return Object.entries(groups);
  }, [events]); // removed currentPage dependency

  const hasFilters = !!(q || type || province || startDate || endDate);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Page Header */}
      <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Danh sách sự kiện
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 flex items-center gap-2">
            Tổng hợp từ 38 nguồn tin chính thống.
            <span className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-black border border-emerald-100/50">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
              HỆ THỐNG TRỰC TUYẾN
            </span>
          </p>
      </div>

      {/* Admin Actions Bar */}
      {isAdmin && (
          <div className="mb-6 flex gap-3 no-print">
              <button 
                  onClick={() => setShowExportView(!showExportView)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all shadow-sm ${showExportView ? 'bg-blue-600 text-white shadow-blue-200' : 'bg-white text-slate-700 border border-slate-200 hover:border-blue-400'}`}
              >
                  <Printer className="w-4 h-4" />
                  <span>{showExportView ? "Quay lại lưới" : "Chế độ Báo cáo Bảng"}</span>
              </button>
              {showExportView && (
                  <>
                    <button 
                        onClick={() => window.print()}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-xl text-sm font-bold hover:bg-black transition-all shadow-md"
                    >
                        <Printer className="w-4 h-4" />
                        <span>In / Xuất PDF</span>
                    </button>
                    <button 
                        disabled={isExporting}
                        onClick={handleExportCSV}
                        className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-xl text-sm font-bold hover:bg-emerald-700 transition-all shadow-md disabled:opacity-50"
                    >
                        {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        <span>{isExporting ? "Đang xuất..." : "Xuất Excel (.xlsx)"}</span>
                    </button>
                    
                    <div className="flex items-center gap-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2 py-1 shadow-sm ml-auto">
                        <select 
                            value={exportMonth} 
                            onChange={(e) => setExportMonth(parseInt(e.target.value))}
                            className="text-xs font-bold bg-transparent outline-none cursor-pointer text-slate-700 dark:text-slate-200"
                        >
                            {[...Array(12).keys()].map(i => <option key={i+1} value={i+1} className="dark:bg-slate-800">Tháng {i+1}</option>)}
                        </select>
                        <select 
                            value={exportYear} 
                            onChange={(e) => setExportYear(parseInt(e.target.value))}
                            className="text-xs font-bold bg-transparent outline-none cursor-pointer text-slate-700 dark:text-slate-200"
                        >
                            {(() => {
                                const currentYear = new Date().getFullYear();
                                return [currentYear - 2, currentYear - 1, currentYear].map(y => <option key={y} value={y} className="dark:bg-slate-800">{y}</option>);
                            })()}
                        </select>
                        <button 
                            disabled={isExporting}
                            onClick={handleExportMonthly}
                            className="ml-2 flex items-center gap-1.5 px-3 py-1 bg-indigo-600 text-white rounded-lg text-[10px] font-black hover:bg-indigo-700 transition-all shadow-sm uppercase tracking-tighter disabled:opacity-50"
                            title="Xuất báo cáo tổng hợp thiệt hại theo tháng"
                        >
                            {isExporting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                            {isExporting ? "XUẤT..." : "BC THÁNG"}
                        </button>
                    </div>
                  </>
              )}
          </div>
      )}

      {/* Styles for Report View */}
      <style>{`
        @media print {
            .no-print { display: none !important; }
            body { background: white !important; padding: 0 !important; margin: 0 !important; }
            .report-table { width: 100% !important; border-collapse: collapse !important; font-size: 10pt !important; }
            .report-table th, .report-table td { border: 1px solid #000 !important; padding: 4px 8px !important; }
            .report-table th { background: #f0f0f0 !important; -webkit-print-color-adjust: exact; }
            .report-container { padding: 0 !important; max-width: 100% !important; }
        }
      `}</style>

      {/* Filter Controls */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 mb-8 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            {/* Search */}
            <div className="lg:col-span-1">
                <input
                    name="q"
                    id="events-q"
                    value={q}
                    onChange={(e) => { setQ(e.target.value); setCurrentPage(1); }}
                    placeholder="Tìm kiếm từ khóa..."
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:bg-white dark:focus:bg-slate-900 transition outline-none"
                />
            </div>
            {/* Type */}
            <div>
                <select 
                    name="type"
                    id="events-type"
                    value={type}
                    onChange={(e) => { setType(e.target.value); setCurrentPage(1); }}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white dark:focus:bg-slate-900 transition outline-none text-slate-700 dark:text-slate-200"
                >
                    <option value="">Tất cả loại hình</option>
                    {Object.entries(DISASTER_METADATA)
                        .filter(([key]) => key !== 'unknown')
                        .map(([key, meta]) => (
                        <option key={key} value={key}>{meta.label}</option>
                    ))}
                </select>
            </div>
            {/* Province */}
            <div>
                <select 
                    name="province"
                    id="events-province"
                    value={province}
                    onChange={(e) => { setProvince(e.target.value); setCurrentPage(1); }}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white dark:focus:bg-slate-900 transition outline-none text-slate-700 dark:text-slate-200"
                >
                    <option value="">Tất cả tỉnh thành</option>
                    {VALID_PROVINCES.map(p => (
                        <option key={p} value={p}>{p}</option>
                    ))}
                </select>
            </div>
            {/* Date Pill (Dashboard Style) */}
            {/* Start Date */}
            <DateFilter 
                dateTime={startDate}
                onChange={(val) => setStartDate(val)}
                placeholder="Từ ngày"
                className="w-full"
            />
            {/* End Date */}
            <DateFilter 
                dateTime={endDate}
                onChange={(val) => setEndDate(val)}
                onClear={clearFilters}
                showClear={hasFilters}
                placeholder="Đến ngày"
                className="w-full"
            />
        </div>
      </div>

      {error ? <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-6">{error}</div> : null}

      {/* Results count */}
       {!loading && events.length > 0 && (
        <div className="mb-6 flex items-center justify-between">
           <div className="text-sm text-slate-600 dark:text-slate-400 font-medium">
             Đang hiển thị <span className="text-slate-900 dark:text-white font-bold">{events.length}</span> sự kiện mới nhất
           </div>
        </div>
      )}

      {loading && events.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in">
            {[...Array(8)].map((_, i) => (
                <div key={i} className="h-full">
                    <EventCardSkeleton />
                </div>
            ))}
        </div>
      ) : showExportView ? (
        /* DAILY REPORT TABLE VIEW */
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-300 dark:border-slate-700 overflow-hidden shadow-xl report-container">
            <div className="p-6 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-center hidden print:block">
                <div className="text-xl font-black uppercase text-slate-900 dark:text-white leading-tight">Báo cáo Tổng hợp Thiên tai Ngày {startDate?.split('-').reverse().join('/')}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 uppercase tracking-widest font-bold">Hệ thống Báo tổng hợp rủi ro thiên tai</div>
            </div>
            <div className="overflow-x-auto">
                <table className="min-w-full report-table">
                    <thead className="bg-slate-800 text-white dark:bg-slate-950">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Ngày</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Loại hình</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Tỉnh Thành</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Xã/Thôn/Tuyến</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Nguyên nhân</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Đặc điểm</th>
                            <th className="px-4 py-3 text-left text-xs font-black uppercase border-b border-slate-700">Thiệt hại</th>
                            {isAdmin && <th className="px-4 py-3 text-center text-xs font-black uppercase no-print border-b border-slate-700">Thao tác</th>}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700 bg-white dark:bg-slate-900">
                        {events.map((e) => (
                            <tr key={e.id} className="hover:bg-blue-50/30 dark:hover:bg-slate-800 transition-colors">
                                <td className="px-4 py-3 text-xs whitespace-nowrap text-slate-700 dark:text-slate-300">{new Date(e.started_at).toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit', year: 'numeric'})}</td>
                                <td className="px-4 py-3 text-xs font-bold text-blue-700 dark:text-blue-400">
                                    <Link to={`/events/${e.id}`} className="hover:underline">
                                        {fmtType(e.disaster_type)}
                                    </Link>
                                </td>
                                <td className="px-4 py-3 text-xs font-bold text-slate-800 dark:text-slate-200">{e.province}</td>
                                <td className="px-4 py-3 text-[11px] leading-tight text-slate-700 dark:text-slate-300">
                                    {e.commune && <div className="font-bold">Xã: {e.commune}</div>}
                                    {e.village && <div>Thôn: {e.village}</div>}
                                    {e.route && <div className="font-mono text-[9px] text-slate-500">{e.route}</div>}
                                </td>
                                <td className="px-4 py-3">
                                   <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase ${e.cause?.includes('Mưa') ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}`}>
                                       {e.cause || "Chưa rõ"}
                                   </span>
                                </td>
                                <td className="px-4 py-3 text-[11px] italic text-slate-600 dark:text-slate-400 line-clamp-3">
                                    {e.characteristics || "N/A"}
                                </td>
                                <td className="px-4 py-3">
                                    <div className="flex flex-wrap gap-1">
                                        {(e.deaths > 0 || e.missing > 0) && <span className="bg-red-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">{e.deaths}C - {e.missing}M</span>}
                                        {e.damage_billion_vnd > 0 && <span className="bg-blue-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">{e.damage_billion_vnd}T</span>}
                                    </div>
                                </td>
                                {isAdmin && (
                                    <td className="px-4 py-3 text-center no-print">
                                        <button 
                                            onClick={(evt) => handleDelete(evt, e.id)}
                                            className="p-1.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-600 hover:text-white dark:hover:text-white rounded-lg transition-all"
                                            title="Xóa sự kiện"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="p-4 bg-slate-50 border-t border-slate-200 text-[10px] italic text-slate-500 text-right print:block hidden">
                Hệ thống tự động trích xuất lúc: {new Date().toLocaleString('vi-VN')}
            </div>
        </div>
      ) : (
        <div className="space-y-12 no-print">
            {groupedEvents.map(([label, items]) => (
            <div key={label} className="space-y-6">
                <div className="flex items-center gap-4">
                <h2 className="text-lg font-black text-slate-800 dark:text-white uppercase tracking-tight flex-shrink-0">
                    {label}
                </h2>
                <div className="h-px bg-slate-200 dark:bg-slate-800 flex-1"></div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {items.map((e) => (
                    <EventCard 
                      key={e.id} 
                      event={e} 
                      isAdmin={isAdmin} 
                      onDelete={(id) => handleDelete({ preventDefault: () => {}, stopPropagation: () => {} }, id)} 
                    />
                ))}
                </div>
            </div>
            ))}

        </div>
      )}

      {/* Pagination Controls (Standard) */}
      {!loading && events.length > 0 && Math.ceil(totalEvents / itemsPerPage) > 1 && !showExportView && (
        <div className="mt-8">
          <Pagination
            currentPage={currentPage}
            totalItems={totalEvents}
            itemsPerPage={itemsPerPage}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Modern Confirm Modal */}
      <ConfirmModal 
        isOpen={showDeleteModal}
        onClose={() => {
            setShowDeleteModal(false);
            setDeleteId(null);
        }}
        onConfirm={confirmDelete}
        title="Xóa sự kiện"
        message="Bạn có chắc chắn muốn xóa sự kiện này? Tất cả các bài báo liên quan sẽ bị gỡ khỏi hệ thống và không thể khôi phục."
        confirmLabel="Xác nhận xóa"
        variant="danger"
      />

      <Toast 
        isVisible={toast.isVisible}
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ ...toast, isVisible: false })}
      />
    </div>
  );
}
