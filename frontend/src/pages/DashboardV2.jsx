import { useEffect, useMemo, useState, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import useDebounce from "../hooks/useDebounce";
import { 
  getJson, 
  fmtType, 
  fmtDate, 
  fmtTimeAgo, 
  cleanText,
  normalizeStr,
  getDisasterMeta,
  toUtcDate
} from "../api.js";
import { THEME_COLORS, DISASTER_METADATA } from "../theme.js";
import StatCard from "../components/StatCard.jsx";
import Badge from "../components/Badge.jsx";
import { VALID_PROVINCES } from "../provinces.js";
import DateFilter from "../components/DateFilter.jsx";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList
} from "recharts";
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  MapPin,
  Calendar,
  Filter,
  RefreshCw,
  ChevronRight,
  Search,
  FileText,
  Bell,
  History
} from "lucide-react";
import { Helmet } from "react-helmet-async";

// No local TYPE_TONES needed anymore

import { useAuth } from "../contexts/AuthContext";
import Pagination from "../components/Pagination.jsx";
import Skeleton, { StatCardSkeleton, NewsItemSkeleton } from "../components/Skeleton.jsx";

// ... existing imports
const getLocalISODate = () => {
    const d = new Date();
    return new Date(d.getTime() - (d.getTimezoneOffset() * 60000)).toISOString().split('T')[0];
};

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [rawEvents, setRawEvents] = useState([]);
  const [articles, setArticles] = useState([]);
  
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [startDate, setStartDate] = useState(searchParams.get("start_date") || getLocalISODate());
  const [endDate, setEndDate] = useState(searchParams.get("end_date") || "");
  
  const [hazardType, setHazardType] = useState(searchParams.get("type") || "all");
  const [provQuery, setProvQuery] = useState(searchParams.get("province") || "");
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  
  // [OPTIMIZATION] Debounce search inputs to avoid API spam on every keystroke
  const debouncedProvQuery = useDebounce(provQuery, 400);
  const debouncedSearchQuery = useDebounce(searchQuery, 400);

  const [quickFilter, setQuickFilter] = useState(searchParams.get("quick") || null);
  const [page, setPage] = useState(parseInt(searchParams.get("page")) || 0);
  const [totalEvents, setTotalEvents] = useState(0); // [NEW] Added for server-side pagination
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString('vi-VN'));
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  // [OPTIMIZATION] Auto-fill favorite province if none is specified in URL
  const initializedFav = useRef(false);
  useEffect(() => {
    if (user?.favorite_province && !initializedFav.current) {
        if (!searchParams.get("province") && !provQuery) {
            setProvQuery(user.favorite_province);
            console.log("[DashboardV2] Auto-applying favorite province:", user.favorite_province);
        }
        initializedFav.current = true;
    }
  }, [user]);

  useEffect(() => {
    // Theme observer for charts reactive to MainLayout toggle
    const observer = new MutationObserver(() => {
        setIsDark(document.documentElement.classList.contains('dark'));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);

    return () => {
        window.removeEventListener("resize", handleResize);
        observer.disconnect();
    };
  }, []);

  const [isDark, setIsDark] = useState(document.documentElement.classList.contains('dark'));
  const isAdmin = user?.role === 'admin';
  const favoriteProvince = user?.favorite_province;


  const events = rawEvents; // Rely on server-side filtering

  const [hotspotsData, setHotspotsData] = useState([]);

  useEffect(() => {
    setPage(0);
  }, [startDate, endDate, hazardType, debouncedProvQuery, debouncedSearchQuery, quickFilter]); // Use debounced values here

  async function load(signal = null, overrides = {}) {
    try {
      setLoading(true);
      setError(null);
      
      // Resolve parameters: Use override if present, else use current debounced state
      const pProv = overrides.province !== undefined ? overrides.province : debouncedProvQuery;
      const pQ = overrides.q !== undefined ? overrides.q : debouncedSearchQuery;
      
      // 1. Construct Main Query (Locked to all filters)
      let queryParams = `?start_date=${startDate}`;
      if (endDate) queryParams += `&end_date=${endDate}`;
      if (hazardType !== "all") queryParams += `&type=${hazardType}`;
      if (pProv) queryParams += `&province=${encodeURIComponent(pProv)}`; 
      if (pQ) queryParams += `&q=${encodeURIComponent(pQ)}`; 
      if (quickFilter) queryParams += `&quick=${quickFilter}`;

      // 2. Construct Context Query (For Hotspots Sidebar - Excludes Province Filter)
      // This ensures the sidebar shows "Context" (e.g. other provinces) even when drilling down into one.
      let contextParams = `?start_date=${startDate}`;
      if (endDate) contextParams += `&end_date=${endDate}`;
      if (hazardType !== "all") contextParams += `&type=${hazardType}`;
      if (pQ) contextParams += `&q=${encodeURIComponent(pQ)}`;
      if (quickFilter) contextParams += `&quick=${quickFilter}`;
      // Note: We purposely OMIT &province here

      // Sidebar articles
      let artParams = `?limit=20`;
      if (hazardType !== "all") artParams += `&type=${hazardType}`;
      if (pProv) artParams += `&province=${encodeURIComponent(pProv)}`; 
      if (pQ) artParams += `&q=${encodeURIComponent(pQ)}`; 

      const needsContextFetch = !!pProv; // Only fetch extra stats if we are actually filtering by province

      const promises = [
        getJson(`/api/stats/summary${queryParams}`, { signal }), // Main Stats (Cards)
        // [OPTIMIZATION] Server-Side Pagination
        getJson(`/api/events${queryParams}&limit=10&offset=${page * 10}&wrapper=true`, { signal }), // Events List with Total Count
        getJson(`/api/articles/latest${artParams}`, { signal }) // Articles
      ];

      if (needsContextFetch) {
          promises.push(getJson(`/api/stats/summary${contextParams}`, { signal })); // Context Stats (Sidebar)
      }

      const results = await Promise.all(promises);
      
      if (signal?.aborted) return;

      const s = results[0];
      const evsData = results[1];
      const arts = results[2];
      const contextS = needsContextFetch ? results[3] : s;

      setStats(s);
      setHotspotsData(contextS.by_province || []); // Use context stats for sidebar
      
      // Handle wrapped response { total, items } vs legacy array
      if (evsData.items) {
          setRawEvents(evsData.items);
          setTotalEvents(evsData.total);
      } else if (Array.isArray(evsData)) {
          setRawEvents(evsData);
          setTotalEvents(evsData.length); // Fallback if API wrapper missing
      } else {
          setRawEvents([]);
          setTotalEvents(0);
      }
      
      setArticles(arts);
      setLastUpdated(new Date().toLocaleTimeString('vi-VN'));

      // Sync to URL
      // Sync to URL
      const newParams = {};
      newParams.start_date = startDate; // Always keep start_date in URL for consistency
      if (endDate) newParams.end_date = endDate;
      if (hazardType !== "all") newParams.type = hazardType;
      if (debouncedProvQuery) newParams.province = debouncedProvQuery;
      if (debouncedSearchQuery) newParams.q = debouncedSearchQuery;
      if (quickFilter) newParams.quick = quickFilter;
      if (page > 0) newParams.page = page;

      const currentParams = Object.fromEntries(searchParams.entries());
      const keys1 = Object.keys(newParams);
      const keys2 = Object.keys(currentParams);
      const isDifferent = keys1.length !== keys2.length || keys1.some(k => String(newParams[k]) !== String(currentParams[k]));
      
      if (isDifferent) {
          setSearchParams(newParams, { replace: true });
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error("Dashboard load error", err);
      setError(err.message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }

  // Handle URL changes (Back button) - Prevent infinite loop
  useEffect(() => {
    const urlStart = searchParams.get("start_date") || getLocalISODate();
    const urlEnd = searchParams.get("end_date") || "";
    const urlType = searchParams.get("type") || "all";
    const urlProv = searchParams.get("province") || "";
    const urlQ = searchParams.get("q") || "";
    const urlQuick = searchParams.get("quick") || null;
    const urlPage = parseInt(searchParams.get("page")) || 0;

    setStartDate(prev => urlStart !== prev ? urlStart : prev);
    setEndDate(prev => urlEnd !== prev ? urlEnd : prev);
    setHazardType(prev => urlType !== prev ? urlType : prev);
    setProvQuery(prev => urlProv !== prev ? urlProv : prev);
    setSearchQuery(prev => urlQ !== prev ? urlQ : prev);
    setQuickFilter(prev => urlQuick !== prev ? urlQuick : prev);
    setPage(prev => urlPage !== prev ? urlPage : prev);
  }, [searchParams]);

  useEffect(() => {
    let controller = new AbortController();
    
    // Initial and dependency-driven load
    load(controller.signal);
    
    // [REAL-TIME] Listen for global refresh signals
    const handleRefresh = () => {
        console.log("[DashboardV2] Real-time signal received, refreshing...");
        // Abort previous if it's still running and start new
        controller.abort();
        controller = new AbortController();
        load(controller.signal);
    };
    window.addEventListener("news:update", handleRefresh);

    const t = setInterval(() => {
        controller.abort();
        controller = new AbortController();
        load(controller.signal);
    }, 300_000); 
    
    return () => {
      controller.abort();
      clearInterval(t);
      window.removeEventListener("news:update", handleRefresh);
    };
  }, [startDate, endDate, hazardType, debouncedProvQuery, debouncedSearchQuery, quickFilter, page]);

  const isToday = startDate === getLocalISODate() && !endDate;

  const handleReset = () => {
    setStartDate(getLocalISODate());
    setEndDate("");
    setProvQuery("");
    setSearchQuery("");
    setHazardType("all");
    setQuickFilter(null);
    setPage(0);
  };

  const chartData = useMemo(() => {
    if (stats && stats.by_type) {
       return Object.entries(stats.by_type)
            .filter(([k]) => k !== 'unknown')
            .map(([k, v]) => ({ 
                name: fmtType(k), 
                count: v,
                fill: THEME_COLORS[k] || THEME_COLORS.unknown
            }))
            .sort((a, b) => b.count - a.count);
    }
    
    // [FIX] Removed fallback logic that used paginated 'events' to represent global stats.
    // If stats.by_type is missing, we prefer showing empty/loading state rather than misleading partial data.
    return [];
  }, [stats]);

  const riskiestHotspots = useMemo(() => {
    // [OPTIMIZATION] Use separate hotspots data to maintain context during filtering
    if (hotspotsData && hotspotsData.length > 0) {
        return hotspotsData;
    }
    return [];
  }, [hotspotsData]);

  const favoriteEvents = useMemo(() => {
    if (!favoriteProvince) return [];
    return rawEvents.filter(e => e.province === favoriteProvince).slice(0, 3);
  }, [rawEvents, favoriteProvince]);

  return (
    <div className="space-y-6">
      <Helmet>
        <title>BÁO TỔNG HỢP RỦI RO THIÊN TAI | Hệ thống theo dõi rủi ro</title>
        <meta name="description" content="Hệ thống tổng hợp và cảnh báo thiên tai sớm từ các cơ quan chính thống tại Việt Nam." />
        <meta property="og:title" content="BÁO TỔNG HỢP RỦI RO THIÊN TAI - Theo dõi rủi ro thời gian thực" />
        <meta property="og:description" content="Theo dõi bão, lũ, sạt lở và các cực đoan thời tiết tại Việt Nam." />
        <meta property="og:image" content="/og-image.png" />
        <meta property="og:type" content="website" />
      </Helmet>
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div className="text-sm font-medium">Lỗi tải dữ liệu: {error}</div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20 rounded-full">
              <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span className="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase tracking-wider">Trực tiếp</span>
          </div>

          <p className="text-slate-500 dark:text-slate-400 flex items-center gap-2 text-xs font-medium">
            <Calendar className="w-3.5 h-3.5" /> 
            Cập nhật: <span className="text-slate-700 dark:text-slate-300">{lastUpdated}</span>
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-2">
           <div className="relative">
              <input
                 type="text"
                 name="province_search"
                 id="dashboard-province-search"
                 placeholder="Tìm theo tỉnh..."
                  value={provQuery}
                  onChange={(e) => setProvQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        load(null, { province: e.currentTarget.value });
                    }
                  }}
                  className="w-40 py-1.5 pl-8 pr-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]/20 dark:text-white transition-all focus:bg-white"
               />
               <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            </div>

            <div className="relative">
               <input
                  type="text"
                  name="event_search"
                  id="dashboard-event-search"
                  placeholder="Tìm tên sự kiện..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        load(null, { q: e.currentTarget.value });
                    }
                  }}
                  className="w-40 py-1.5 pl-8 pr-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]/20 dark:text-white transition-all focus:bg-white"
               />
               <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            </div>

            <div className="relative">
                <select
                    name="hazard_type"
                    id="dashboard-hazard-type"
                    aria-label="Lọc theo loại hình thiên tai"
                    value={hazardType}
                    onChange={(e) => setHazardType(e.target.value)}
                    className="appearance-none bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium py-1.5 pl-3 pr-8 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2fa1b3]/20 cursor-pointer transition-all hover:bg-white dark:hover:bg-slate-700"
                >
                    <option value="all">Tất cả thông tin</option>
                    {Object.entries(DISASTER_METADATA)
                        .filter(([key]) => key !== 'unknown')
                        .map(([key, meta]) => (
                        <option key={key} value={key}>{meta.label}</option>
                    ))}
                </select>
               <Filter className="w-3 h-3 text-slate-400 dark:text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
           </div>

            <DateFilter 
              dateTime={startDate}
              onChange={(val) => {
                  setStartDate(val);
                  setEndDate("");
              }}
              className="min-w-[120px]"
            />

            <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block"></div>

            <div className="flex items-center gap-1.5">
              <button 
                onClick={() => load()}
                title="Cập nhật dữ liệu mới nhất (Refresh)"
                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-[#2fa1b3] transition-all group flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 group-hover:rotate-180 transition-transform duration-700 ${loading ? 'animate-spin' : ''}`} />
                <span className="text-[10px] font-bold uppercase text-slate-500">Cập nhật</span>
              </button>

              <button 
                onClick={handleReset}
                title="Xóa bộ lọc / Xem mặc định (Reset)"
                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500 transition-all group flex items-center gap-2"
              >
                <History className={`w-4 h-4 group-hover:rotate-180 transition-transform duration-500`} />
                <span className="text-[10px] font-bold uppercase text-slate-500">Mặc định</span>
              </button>
            </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {loading && !stats ? (
            <>
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
            </>
        ) : (
            <>
                <StatCard
                title={isToday ? "Sự kiện mới (24h)" : `Sự kiện ngày ${startDate}`}
                value={stats?.events_count || 0}
                sub={stats?.needs_verification_count ? `${stats.needs_verification_count} tin cần xác minh` : "Dữ liệu thời gian thực"}
                icon={Activity}
                trend={stats?.events_count > 0 ? "up" : "neutral"}
                color="brand"
                active={quickFilter === null}
                onClick={() => setQuickFilter(null)}
                />
                <StatCard
                title="Tỉnh ảnh hưởng"
                value={stats?.provinces_count || 0}
                sub="Ghi nhận trong kỳ"
                icon={MapPin}
                color="brand"
                active={quickFilter === "provinces"}
                onClick={() => setQuickFilter(quickFilter === "provinces" ? null : "provinces")}
                />
                <StatCard
                title="Báo cáo cộng đồng"
                value={stats?.community_reports_count || 0}
                sub="Thông tin từ hiện trường"
                icon={Bell}
                color="violet"
                active={quickFilter === "community"}
                onClick={() => setQuickFilter(quickFilter === "community" ? null : "community")}
                />
                <StatCard
                title="Thiệt hại người"
                value={stats?.events_with_human_damage || 0}
                sub="Vụ việc có thương vong"
                icon={AlertTriangle}
                color="red"
                active={quickFilter === "casualties"}
                onClick={() => setQuickFilter(quickFilter === "casualties" ? null : "casualties")}
                />
                <StatCard
                title="Thiệt hại tài sản"
                value={stats?.events_with_property_damage || 0}
                sub="Vụ việc có mất mát tài sản"
                icon={TrendingUp}
                color="emerald"
                active={quickFilter === "damage"}
                onClick={() => setQuickFilter(quickFilter === "damage" ? null : "damage")}
                />
            </>
        )}
      </div>


      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col h-full transition-all duration-300">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-white dark:bg-slate-900">
              <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" /> Danh sách sự kiện
              </h3>
              <Link to="/events" className="text-xs flex items-center gap-1 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors">
                Xem tất cả <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
            
            {/* Highlights for favorite area */}
            {favoriteProvince && favoriteEvents.length > 0 && (
              <div className="bg-blue-50/50 dark:bg-blue-900/10 p-4 border-b border-blue-100 dark:border-blue-900/30">
                <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-bold text-xs uppercase tracking-wider mb-3">
                   <Bell className="w-3.5 h-3.5 animate-bounce" />
                   Thiên tai tại {favoriteProvince}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                   {favoriteEvents.map(e => (
                     <Link key={e.id} to={`/events/${e.id}`} className="bg-white dark:bg-slate-800 p-3 rounded-xl border border-blue-200 dark:border-blue-900/40 shadow-sm hover:shadow-md transition-all flex flex-col group/fav">
                        <Badge tone={getDisasterMeta(e.disaster_type).tone} className="w-fit px-1.5 py-0.5 text-[8px] mb-2">
                           {fmtType(e.disaster_type)}
                        </Badge>
                        <h5 className="font-bold text-slate-900 dark:text-white text-[11px] leading-tight line-clamp-2 group-hover/fav:text-blue-600 transition-colors">{e.title}</h5>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-2">{fmtTimeAgo(e.last_updated_at)}</span>
                     </Link>
                   ))}
                </div>
              </div>
            )}

            <div className={`divide-y divide-slate-100 dark:divide-slate-800 flex-1 min-h-[400px] relative transition-all duration-500`}>
              {loading && events.length === 0 ? (
                <>
                    <NewsItemSkeleton />
                    <NewsItemSkeleton />
                    <NewsItemSkeleton />
                    <NewsItemSkeleton />
                    <NewsItemSkeleton />
                </>
              ) : (
                events.map((event) => (
                    <div key={event.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all group relative border-l-4 border-transparent hover:border-blue-500/30">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <Badge tone={getDisasterMeta(event.disaster_type).tone} className="px-1.5 py-0.5 text-[9px] uppercase font-black">
                            {fmtType(event.disaster_type)}
                          </Badge>
                        </div>
                      </div>
                      <Link to={`/events/${event.id}`}>
                        <h4 className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2 mb-2 text-sm leading-tight group-hover:translate-x-1 transition-transform">
                          {cleanText(event.title)}
                        </h4>
                      </Link>
                      <div className="flex items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="flex items-center gap-1"><MapPin className="w-3 h-3 text-slate-400" /> {event.province || "Đang xác minh"}</span>
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3 text-slate-400" /> {event.started_at ? toUtcDate(event.started_at).toLocaleDateString('vi-VN') : "—"}</span>
                      </div>
                    </div>
                  ))
              )}
              
              {!loading && events.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 text-slate-500 dark:text-slate-400 text-sm">
                   <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                      <AlertTriangle className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                   </div>
                   <p className="font-bold text-slate-400 uppercase tracking-widest text-[11px]">Không tìm thấy sự kiện nào khớp với bộ lọc</p>
                   <button 
                      onClick={handleReset}
                      className="mt-4 text-xs font-bold text-[#2fa1b3] hover:underline"
                   >
                      ĐẶT LẠI BỘ LỌC
                   </button>
                </div>
              )}
            </div>

            {/* Pagination Controls - Fixed at Bottom */}
            {totalEvents > 10 && (
              <div className="mt-auto p-4 border-t border-slate-100 flex justify-center bg-slate-50/30">
                <Pagination 
                  currentPage={page + 1} // Pagination component uses 1-index
                  totalItems={totalEvents}
                  itemsPerPage={10}
                  onPageChange={(p) => setPage(p - 1)} // API uses 0-index
                />
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 transition-all duration-300">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" /> Điểm nóng rủi ro
            </h3>
            <div className="space-y-1">
              {riskiestHotspots?.length > 0 ? (
                riskiestHotspots.slice(0, 15).map((p, idx) => {
                  const isActive = provQuery === p.province;
                  return (
                    <button 
                      key={p.province} 
                      onClick={() => setProvQuery(isActive ? "" : p.province)}
                      className={`w-full flex items-center justify-between py-1.5 px-2 rounded-lg transition-all ${
                        isActive 
                          ? "bg-blue-50 dark:bg-blue-900/40 border border-blue-100 dark:border-blue-800 shadow-sm" 
                          : "hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`w-5 h-5 flex items-center justify-center rounded-md text-[10px] font-bold ${
                          idx < 3 ? 'bg-orange-100 dark:bg-orange-900/40 text-orange-600' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                        }`}>
                          {idx + 1}
                        </span>
                        <span className={`text-xs font-medium ${isActive ? 'text-blue-600 dark:text-blue-400 font-bold' : ''}`}>{p.province}</span>
                      </div>
                      <span className="text-[10px] font-bold bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-500">{p.events} vụ</span>
                    </button>
                  );
                })
              ) : (
                <div className="text-center py-10 text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
                  Không có điểm nóng<br/>trong khu vực/thời gian này
                </div>
              )}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 transition-all duration-300">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Phân loại thiên tai</h3>
            <div className={windowWidth < 640 ? "h-64" : "h-96"}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 5, right: 30 }} barCategoryGap="15%">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" className="dark:opacity-10" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={windowWidth < 640 ? 100 : 140} tick={{ fontSize: windowWidth < 640 ? 9 : 10, fill: '#64748b' }} />
                  <Tooltip 
                    cursor={{fill: '#f1f5f9', opacity: 0.1}} 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', backgroundColor: isDark ? '#1e293b' : '#fff', color: isDark ? '#fff' : '#000' }}
                  />
                  <Bar 
                    dataKey="count" 
                    radius={[0, 4, 4, 0]} 
                    barSize={windowWidth < 640 ? 18 : 24}
                    isAnimationActive={true}
                    animationDuration={1500}
                    animationBegin={200}
                  >
                    {chartData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                    <LabelList dataKey="count" position="right" fontSize={windowWidth < 640 ? 10 : 12} fontWeight={600} fill="#64748b" /> 
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
