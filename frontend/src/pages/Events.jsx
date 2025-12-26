import { useEffect, useState, useMemo, useRef } from "react";
import {
  getJson,
  deleteJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
  cleanText,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import { THEME_COLORS } from "../theme.js";
import { MapPin, Clock, FileText, Zap, DollarSign, Users, Activity, Filter, X, CloudRainWind, Waves, Sun, Flame, Wind, Mountain, AlertTriangle, ArrowRight, Calendar, Trash2 } from "lucide-react";
import logoIge from "../assets/logo_ige.png";

// Updated tones for 8 groups
const TYPE_TONES = {
  storm: "blue",
  flood: "cyan",
  flash_flood: "cyan",
  landslide: "orange",
  subsidence: "slate",
  drought: "orange",
  salinity: "blue",
  extreme_weather: "yellow",
  heatwave: "red",
  cold_surge: "indigo",
  earthquake: "slate",
  tsunami: "blue",
  storm_surge: "purple",
  wildfire: "red",
  warning_forecast: "yellow",
  recovery: "emerald",
  unknown: "slate",
};

// Extract provinces for dropdown
// Must match PROVINCE_MAPPING keys in backend/app/nlp.py
const PROVINCES = [
  "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên",
  "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh",
  "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình",
  "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế",
  "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa",
  "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp",
  "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
].sort();

export default function Events() {
  const dateInputRef = useRef(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [province, setProvince] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState("");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 40;
  
  const [error, setError] = useState(null);
  const [isAdmin, setIsAdmin] = useState(!!localStorage.getItem("access_token"));

  const handleDelete = async (e, eventId) => {
    e.preventDefault(); // Prevent navigation
    if (!window.confirm("Bạn có chắc chắn muốn xóa sự kiện này? Bài viết liên quan sẽ bị loại bỏ khỏi hệ thống.")) return;

    try {
      await deleteJson(`/api/events/${eventId}`);
      // Remove from local state immediately
      setEvents(prev => prev.filter(ev => ev.id !== eventId));
    } catch (err) {
      alert("Xóa thất bại: " + err.message);
    }
  };

  /* Helper to normalize string for search (remove tones and spaces) */
  const normalizeStr = (str, removeSpaces = false) => {
    if (!str) return "";
    let res = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (removeSpaces) res = res.replace(/\s+/g, '');
    return res;
  }

  const fetchEvents = async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      setError(null);
      
      // Fetch base data first (filtered by Category on server for efficiency)
      const params = new URLSearchParams();
      params.append("limit", "400"); // 40 items * 10 pages
      params.append("sort", "latest");
      
      if (type) params.append("type", type);
      
      // Use startDate as the 'Ceiling' to fill the list chronologically backwards
      if (startDate) params.append("end_date", startDate);
      if (endDate) params.append("start_date", endDate); // Inversed or dual range if needed
      
      const evs = await getJson(`/api/events?${params.toString()}`);
      
      let filteredEvents = evs.filter((e) => e.disaster_type && e.disaster_type !== "unknown");

      // Client-side smart filtering for Text and Province (unaccented support)
      if (q) {
          const query = normalizeStr(q, true);
          filteredEvents = filteredEvents.filter(e => e.title && normalizeStr(e.title, true).includes(query));
      }
      if (province) {
          // Special cases for HCM / HN
          let query = normalizeStr(province, true);
          if (query === "tphochiminh") query = "hochiminh"; // allow matching "TP. Hồ Chí Minh" with just "hochiminh"
          
          filteredEvents = filteredEvents.filter(e => {
            if (!e.province) return false;
            let target = normalizeStr(e.province, true);
            return target.includes(query) || query.includes(target);
          });
      }
      
      // Sort by newest first
      filteredEvents.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
      
      setEvents(filteredEvents);
      // Only reset page on explicit filter change (user interaction), NOT on background refresh
      // But here we can't easily distinguish generic 'fetch' from 'filter change' using just this function.
      // Ideally, setCurrentPage(1) should be called by the filter setters or a separate effect tracking filter changes.
      // For now, we'll assume if it's NOT background, it might be a filter change or initial load.
      if (!isBackground) setCurrentPage(1);
      
    } catch (e) {
      console.error("Fetch error:", e);
      if (!isBackground) setError(e.message || "Load failed");
    } finally {
      if (!isBackground) setLoading(false);
    }
  };

  // Initial load & Filter change
  useEffect(() => {
    fetchEvents(false);
  }, [q, type, province, startDate, endDate]);

  // Auto-refresh every 15 seconds (reduced from 60s for better responsiveness)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchEvents(true);
    }, 15000); // 15 seconds
    return () => clearInterval(interval);
  }, [q, type, province, startDate, endDate]);

  const clearFilters = () => {
    setQ("");
    setType("");
    setProvince("");
    setStartDate(new Date().toISOString().split('T')[0]);
    setEndDate("");
    setCurrentPage(1);
  };

  // Pagination logic
  const totalPages = Math.ceil(events.length / itemsPerPage);

  // Group events by date for rendering
  const groupedEvents = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const currentEvents = events.slice(startIndex, startIndex + itemsPerPage);
    
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
  }, [events, currentPage, itemsPerPage]);

  const hasFilters = q || type || province || startDate || endDate;

  // Check if image is a generic Google News logo or broken
  const isJunkImage = (url) => {
    if (!url) return true;
    const junkPatterns = [
        'googleusercontent.com', 
        'gstatic.com', 
        'news_logo', 
        'default_image',
        'placeholder',
        'tabler-icons', // Treat backend default SVGs as junk/placeholder
        'triangle.svg',
        'droplet.svg'
    ];
    return junkPatterns.some(p => url.toLowerCase().includes(p));
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Page Header */}
      <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Danh sách sự kiện
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Tổng hợp sự kiện thiên tai từ 38 nguồn tin tức chính thống.
          </p>
      </div>

      {/* Filter Controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-8 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            {/* Search */}
            <div className="lg:col-span-1">
                <input
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    placeholder="Tìm kiếm từ khóa..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white transition outline-none"
                />
            </div>
            {/* Type */}
            <div>
                <select 
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white transition outline-none text-slate-700"
                >
                    <option value="">Tất cả loại hình</option>
                    <option value="storm">Bão, ATNĐ</option>
                    <option value="flood">Lũ lụt</option>
                    <option value="flash_flood">Lũ quét</option>
                    <option value="landslide">Sạt lở đất</option>
                    <option value="subsidence">Sụt lún</option>
                    <option value="drought">Hạn hán</option>
                    <option value="salinity">Xâm nhập mặn</option>
                    <option value="extreme_weather">Mưa lớn, Lốc, Đá</option>
                    <option value="heatwave">Nắng nóng</option>
                    <option value="cold_surge">Rét hại, Băng giá</option>
                    <option value="earthquake">Động đất</option>
                    <option value="tsunami">Sóng thần</option>
                    <option value="storm_surge">Nước dâng</option>
                    <option value="wildfire">Cháy rừng</option>
                    <option value="warning_forecast">Tin dự báo</option>
                    <option value="recovery">Khắc phục</option>
                </select>
            </div>
            {/* Province */}
            <div>
                <select 
                    value={province}
                    onChange={(e) => setProvince(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white transition outline-none text-slate-700"
                >
                    <option value="">Tất cả tỉnh thành</option>
                    {PROVINCES.map(p => (
                        <option key={p} value={p}>{p}</option>
                    ))}
                </select>
            </div>
            {/* Date Pill (Dashboard Style) */}
            <div className="flex items-center gap-2">
                <div 
                    onClick={() => dateInputRef.current?.showPicker()}
                    className="flex-1 flex items-center justify-between gap-2 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 hover:border-blue-400 hover:bg-white transition-all cursor-pointer shadow-sm group"
                >
                    <span className="text-sm font-bold text-slate-700">
                        {startDate ? startDate.split('-').reverse().join('/') : "Tất cả thời gian"}
                    </span>
                    <Calendar className="w-4 h-4 text-blue-500 group-hover:scale-110 transition-transform" />
                    <input 
                        ref={dateInputRef}
                        type="date"
                        value={startDate} 
                        onChange={(e) => {
                            setStartDate(e.target.value);
                            setEndDate(""); 
                        }}
                        className="absolute opacity-0 pointer-events-none"
                    />
                </div>
                {hasFilters && (
                    <button 
                         onClick={clearFilters}
                         className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors border border-slate-200 shadow-sm"
                         title="Xóa bộ lọc"
                    >
                         <X className="w-5 h-5" />
                    </button>
                )}
            </div>
        </div>
      </div>

      {error ? <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-6">{error}</div> : null}

      {/* Results count */}
      {!loading && events.length > 0 && (
        <div className="mb-6 flex items-center justify-between">
           <div className="text-sm text-slate-600 font-medium">
             Hiển thị <span className="text-slate-900">{(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, events.length)}</span> trong tổng số <span className="text-slate-900">{events.length}</span> sự kiện
           </div>
           {Math.ceil(events.length / itemsPerPage) > 1 && (
             <div className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-md font-bold">
                TRANG {currentPage} / {Math.ceil(events.length / itemsPerPage)}
             </div>
           )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-slate-300 border-t-blue-600"></div>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          Không tìm thấy sự kiện nào phù hợp.
        </div>
      ) : (
        <div className="space-y-12">
            {groupedEvents.map(([label, items]) => (
            <div key={label} className="space-y-6">
                <div className="flex items-center gap-4">
                <h2 className="text-lg font-black text-slate-800 uppercase tracking-tight flex-shrink-0">
                    {label}
                </h2>
                <div className="h-px bg-slate-200 flex-1"></div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {items.map((e) => (
                    <a
                    key={e.id}
                    href={`/events/${e.id}`}
                    className="block group bg-white rounded-2xl border-2 hover:shadow-2xl hover:-translate-y-1 transition-all duration-500 flex flex-col overflow-hidden relative shadow-sm"
                    style={{ borderColor: THEME_COLORS[e.disaster_type] || THEME_COLORS.unknown }}
                    >
                    <div className="h-1 w-full" style={{ backgroundColor: THEME_COLORS[e.disaster_type] || THEME_COLORS.unknown }}></div>
                    <div className="w-full h-44 overflow-hidden relative flex items-center justify-center bg-slate-100/30">
                        {!isJunkImage(e.image_url) ? (
                            <img 
                                src={e.image_url} 
                                alt={e.title} 
                                className={
                                    e.image_url.endsWith('.svg')
                                    ? "w-24 h-24 object-contain opacity-50 transition-transform duration-500 group-hover:scale-110" 
                                    : "w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000"
                                }
                            />
                        ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center p-4 bg-white">
                                <img 
                                    src={logoIge} 
                                    alt="Logo IGE" 
                                    className="w-28 h-28 object-contain opacity-95 group-hover:scale-110 transition-transform duration-700" 
                                    style={{ mixBlendMode: 'multiply' }}
                                />
                                <div className="mt-3 h-1.5 w-16 rounded-full" style={{ backgroundColor: THEME_COLORS[e.disaster_type] || THEME_COLORS.unknown }}></div>
                            </div>
                        )}
                        <div className="absolute top-4 left-4 flex flex-col items-start gap-2">
                            <Badge tone={TYPE_TONES[e.disaster_type] || "slate"} className="shadow-md">
                                {fmtType(e.disaster_type)}
                            </Badge>
                            {e.needs_verification === 1 && (e.deaths > 0 || e.missing > 0 || e.damage_billion_vnd >= 1) && (
                                <div className="bg-red-600 text-white text-[9px] font-black uppercase px-2 py-0.5 rounded-full shadow-lg border border-red-400/30">
                                    Cần kiểm chứng
                                </div>
                            )}
                        </div>
                        {isAdmin && (
                            <button 
                                onClick={(evt) => handleDelete(evt, e.id)}
                                className="absolute top-4 right-4 p-2 bg-white/90 backdrop-blur-sm hover:bg-red-50 text-slate-400 hover:text-red-500 rounded-lg shadow-sm transition-colors z-20 border border-slate-100"
                                title="Xóa sự kiện (Admin)"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        )}
                        </div>

                    <div className="p-5 flex-1 flex flex-col">
                        <h2 className="text-[15px] font-bold text-slate-900 line-clamp-2 mb-3 group-hover:text-blue-600 transition-colors leading-snug h-11">
                            {cleanText(e.title)}
                        </h2>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500 mb-5">
                            {e.province && (
                            <div className="flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded-md">
                                <MapPin className="w-3 h-3 text-slate-400" />
                                <span className="font-medium">{e.province}</span>
                            </div>
                            )}
                            <div className="flex items-center gap-1 font-medium">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>{fmtTimeAgo(e.started_at)}</span>
                            </div>
                            {e.source && (
                            <span className="font-bold text-red-500 uppercase ml-auto">{e.source}</span>
                            )}
                        </div>

                        <div className="flex flex-wrap gap-2 mb-4 min-h-[32px]">
                            {(() => {
                            const prioritized = [];
                            const details = e.details || {};
                            
                            // 1. Core Human Casualties
                            if (e.deaths > 0) prioritized.push({ type: 'deaths', label: `${e.deaths} chết`, priority: 100, color: 'red', icon: Zap });
                            if (e.missing > 0) prioritized.push({ type: 'missing', label: `${e.missing} mất tích`, priority: 90, color: 'orange', icon: Users });
                            if (e.injured > 0) prioritized.push({ type: 'injured', label: `${e.injured} bị thương`, priority: 80, color: 'yellow', icon: Activity });

                            // 2. Financial
                            if (e.damage_billion_vnd > 0) prioritized.push({ type: 'damage', label: fmtVndBillion(e.damage_billion_vnd), priority: 70, color: 'blue', icon: DollarSign });
                            
                            // 3. Other Details
                            if (details.homes && details.homes.length > 0) {
                                const best = details.homes.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.homes[0]);
                                prioritized.push({ type: 'homes', label: `${best.num} ${best.unit || 'nhà'}`, priority: 60, color: 'indigo', icon: MapPin });
                            }
                            if (details.disruption && details.disruption.length > 0) {
                                const best = details.disruption.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.disruption[0]);
                                prioritized.push({ type: 'disruption', label: `${best.num} ${best.unit || 'di dời'}`, priority: 55, color: 'slate', icon: Users });
                            }
                            if (details.agriculture && details.agriculture.length > 0) {
                                const best = details.agriculture.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.agriculture[0]);
                                prioritized.push({ type: 'agriculture', label: `${best.num} ${best.unit || 'ha'}`, priority: 50, color: 'green', icon: Filter });
                            }
                            if (details.marine && details.marine.length > 0) {
                                const best = details.marine.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.marine[0]);
                                prioritized.push({ type: 'marine', label: `${best.num} ${best.unit || 'tàu'}`, priority: 45, color: 'cyan', icon: Activity });
                            }
                            
                            prioritized.sort((a, b) => b.priority - a.priority);
                            
                            // Show only the top 2 most important stats
                            return prioritized.slice(0, 2).map((item) => {
                                const Icon = item.icon;
                                const colorClass = { 
                                    red: "text-red-700 bg-red-50 border border-red-100",
                                    orange: "text-orange-700 bg-orange-50 border border-orange-100",
                                    yellow: "text-yellow-700 bg-yellow-50 border border-yellow-100",
                                    blue: "text-blue-700 bg-blue-50 border border-blue-100", 
                                    indigo: "text-indigo-700 bg-indigo-50 border border-indigo-100", 
                                    slate: "text-slate-700 bg-slate-50 border border-slate-100",
                                    green: "text-emerald-700 bg-emerald-50 border border-emerald-100",
                                    cyan: "text-cyan-700 bg-cyan-50 border border-cyan-100"
                                }[item.color] || "text-slate-700 bg-slate-50";
                                
                                return (
                                    <div key={item.type} className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1.5 rounded-lg shadow-sm ${colorClass}`}>
                                        <Icon className="w-3.5 h-3.5" />
                                        <span>{item.label}</span>
                                    </div>
                                );
                            });
                            })()}
                        </div>

                        <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                            <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1 text-slate-500">
                                <FileText className="w-3.5 h-3.5" />
                                <span>{e.sources_count || 1} nguồn</span>
                            </div>
                            </div>
                            <span className="text-slate-400 font-medium">{new Date(e.started_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>
                    </div>
                    </a>
                ))}
                </div>
            </div>
            ))}
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && events.length > 0 && totalPages > 1 && (
        <div className="mt-8 flex justify-center items-center gap-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Quay lại
          </button>
          
          <div className="flex gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
               // Show 5 pages window
               let start = Math.max(1, currentPage - 2);
               if (start + 4 > totalPages) start = Math.max(1, totalPages - 4);
               const p = start + i;
               
               return (
                <button
                    key={p}
                    onClick={() => setCurrentPage(p)}
                    className={`w-9 h-9 rounded-lg text-sm font-bold transition-colors ${
                      currentPage === p 
                        ? "bg-blue-600 text-white shadow-md shadow-blue-200" 
                        : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                    }`}
                >
                    {p}
                </button>
               );
            })}
          </div>

          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Tiếp theo
          </button>
        </div>
      )}
    </div>
  );
}
