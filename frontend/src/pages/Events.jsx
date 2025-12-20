import { useEffect, useState, useMemo } from "react";
import {
  getJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import { MapPin, Clock, FileText, Zap, DollarSign, Users, Activity, Filter, X } from "lucide-react";

// Updated tones for 8 groups
const TYPE_TONES = {
  storm: "blue", // Bão
  flood_landslide: "cyan", // Mưa lũ
  heat_drought: "orange", // Nắng nóng
  wind_fog: "slate", // Gió
  storm_surge: "purple", // Nước dâng
  extreme_other: "red", // Cực đoan khác
  wildfire: "amber", // Cháy rừng
  quake_tsunami: "green", // Động đất
  unknown: "slate",
};

// Extract provinces for dropdown
// Must match PROVINCE_MAPPING keys in backend/app/nlp.py
const PROVINCES = [
  "Thủ đô Hà Nội", "Cao Bằng", "Tuyên Quang", "Lào Cai", "Điện Biên", "Lai Châu", "Sơn La", 
  "Thái Nguyên", "Lạng Sơn", "Quảng Ninh", "Phú Thọ", "Bắc Ninh", "Hải Phòng", "Hưng Yên", 
  "Ninh Bình", "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "Huế", "Đà Nẵng", 
  "Quảng Ngãi", "Khánh Hòa", "Gia Lai", "Đắk Lắk", "Lâm Đồng", "Tây Ninh", "Đồng Nai", 
  "Thành phố Hồ Chí Minh", "Vĩnh Long", "Đồng Tháp", "An Giang", "Cần Thơ", "Cà Mau"
].sort();

export default function Events() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [province, setProvince] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 24;
  
  const [error, setError] = useState(null);

  /* Helper to normalize string for search (remove tones) */
  const normalizeStr = (str) => {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch base data first (filtered by Type and Date on server for efficiency)
        const params = new URLSearchParams();
        params.append("limit", "200"); // Get enough data 
        if (type) params.append("type", type);
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);
        // Note: We don't send 'q' and 'province' to server anymore to support smart local filtering

        const evs = await getJson(`/api/events?${params.toString()}`);
        
        let filteredEvents = evs.filter((e) => e.disaster_type && e.disaster_type !== "unknown");

        // Client-side smart filtering for Text and Province (unaccented support)
        if (q) {
            const query = normalizeStr(q);
            filteredEvents = filteredEvents.filter(e => e.title && normalizeStr(e.title).includes(query));
        }
        if (province) {
            const query = normalizeStr(province);
            filteredEvents = filteredEvents.filter(e => e.province && normalizeStr(e.province).includes(query));
        }
        
        setEvents(filteredEvents);
        setCurrentPage(1);
      } catch (e) {
        setError(e.message || "Load failed");
      } finally {
        setLoading(false);
      }
    })();
  }, [q, type, province, startDate, endDate]);

  const clearFilters = () => {
      setQ("");
      setType("");
      setProvince("");
      setStartDate("");
      setEndDate("");
      setCurrentPage(1);
  };

  // Pagination logic
  const totalPages = Math.ceil(events.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentEvents = events.slice(startIndex, endIndex);

  const hasFilters = q || type || province || startDate || endDate;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
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
                    <option value="flood_landslide">Mưa lớn, Lũ, Lũ quét, Sạt lở</option>
                    <option value="heat_drought">Nắng nóng, Hạn hán, Xâm nhập mặn</option>
                    <option value="wind_fog">Gió mạnh trên biển, Sương mù</option>
                    <option value="storm_surge">Nước dâng</option>
                    <option value="extreme_other">Lốc, Sét, Mưa đá, Rét hại, Sương muối</option>
                    <option value="wildfire">Cháy rừng</option>
                    <option value="quake_tsunami">Động đất, Sóng thần</option>
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
            {/* Date Range - Simplified to Start Date for now or range logic */}
            <div>
                 <input 
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white transition outline-none text-slate-700"
                    placeholder="Từ ngày"
                 />
            </div>
            <div className="flex gap-2">
                 <input 
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:bg-white transition outline-none text-slate-700"
                    placeholder="Đến ngày"
                 />
                 {hasFilters && (
                     <button 
                        onClick={clearFilters}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
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
        <div className="mb-4 text-sm text-slate-600">
          Hiển thị {startIndex + 1}-{Math.min(endIndex, events.length)} trong tổng số {events.length} sự kiện
          {totalPages > 1 && ` (Trang ${currentPage}/${totalPages})`}
        </div>
      )}

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {currentEvents.map((e) => (
          <a
            key={e.id}
            href={`/events/${e.id}`}
            className="block group bg-white rounded-2xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all duration-300 flex flex-col overflow-hidden relative"
          >
            {/* Top Border Indicator */}
            <div className="h-1.5 w-full bg-blue-500"></div>
            
            {/* 0. Image Area */}
            <div className="w-full h-48 bg-slate-100 overflow-hidden relative">
                 {e.image_url ? (
                    <img 
                      src={e.image_url} 
                      alt={e.title} 
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                 ) : (
                    <div className="w-full h-full flex items-center justify-center bg-slate-100 text-slate-300">
                        <Activity className="w-12 h-12 opacity-20" />
                    </div>
                 )}
                 {/* Badge Overlay */}
                 <div className="absolute top-3 left-3 flex flex-col gap-2">
                    <Badge tone={TYPE_TONES[e.disaster_type] || "slate"}>
                       {fmtType(e.disaster_type)}
                    </Badge>
                 </div>
            </div>

            {/* 1. Header: Title + Province */}
            <div className="p-5 flex-1 flex flex-col">
               <h2 className="text-base font-semibold text-slate-900 line-clamp-2 mb-3 group-hover:text-blue-600 transition-colors">
                  {e.title}
               </h2>
               
               {/* Province + Time */}
               <div className="flex items-center gap-3 text-xs text-slate-500 mb-4">
                  {e.province && (
                     <div className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" />
                        <span>{e.province}</span>
                     </div>
                  )}
                  <div className="flex items-center gap-1">
                     <Clock className="w-3.5 h-3.5" />
                     <span>{fmtTimeAgo(e.started_at)}</span>
                  </div>
                  {e.source && (
                     <span className="font-semibold text-red-600 uppercase text-[10px]">
                        {e.source}
                     </span>
                  )}
               </div>


               {/* 2. Impact Stats Grid (Dynamic & Prioritized) */}
               <div className="flex flex-wrap gap-2 mb-4">
                  {(() => {
                    const prioritized = [];
                    const details = e.details || {};

                    // 1. Core Human Casualties (from columns)
                    if (e.deaths > 0) prioritized.push({ type: 'deaths', label: `${e.deaths} chết`, priority: 100, color: 'red' , icon: Zap });
                    if (e.missing > 0) prioritized.push({ type: 'missing', label: `${e.missing} mất tích`, priority: 90, color: 'orange', icon: Users });
                    if (e.injured > 0) prioritized.push({ type: 'injured', label: `${e.injured} bị thương`, priority: 80, color: 'yellow', icon: Activity });

                    // 2. Financial (from column)
                    if (e.damage_billion_vnd > 0) prioritized.push({ type: 'damage', label: fmtVndBillion(e.damage_billion_vnd), priority: 70, color: 'blue', icon: DollarSign });

                    // 3. Extended details (from JSON)
                    // Check 'homes'
                    if (details.homes && details.homes.length > 0) {
                        // Take the largest number or first
                        const best = details.homes.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.homes[0]);
                        prioritized.push({ 
                            type: 'homes', 
                            label: `${best.num} ${best.unit || 'nhà'}`, // e.g. "50 nhà", "50 tốc mái"
                            priority: 60, 
                            color: 'indigo',
                            icon: MapPin // Placeholder icon
                        });
                    }
                    
                    // Check 'disruption' (evacuation)
                    if (details.disruption && details.disruption.length > 0) {
                        const best = details.disruption.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.disruption[0]);
                         prioritized.push({ 
                            type: 'disruption', 
                            label: `${best.num} ${best.unit || 'di dời'}`, 
                            priority: 55, 
                            color: 'slate',
                            icon: Users
                        });
                    }

                    // Check 'agriculture'
                    if (details.agriculture && details.agriculture.length > 0) {
                        const best = details.agriculture.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.agriculture[0]);
                        prioritized.push({ 
                            type: 'agriculture', 
                            label: `${best.num} ${best.unit || 'ha'}`, 
                            priority: 40, 
                            color: 'green',
                            icon: Filter
                        });
                    }

                    // Check 'marine'
                    if (details.marine && details.marine.length > 0) {
                        const best = details.marine.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.marine[0]);
                        prioritized.push({ 
                            type: 'marine', 
                            label: `${best.num} ${best.unit || 'tàu'}`, 
                            priority: 30, 
                            color: 'cyan',
                            icon: Activity
                        });
                    }

                    // Sort by priority desc
                    prioritized.sort((a, b) => b.priority - a.priority);

                    // Show top 4
                    return prioritized.slice(0, 4).map((item) => {
                        const Icon = item.icon;
                        const colorClass = {
                            red: "text-red-700 bg-red-50",
                            orange: "text-orange-700 bg-orange-50",
                            yellow: "text-yellow-700 bg-yellow-50",
                            blue: "text-blue-700 bg-blue-50",
                            indigo: "text-indigo-700 bg-indigo-50",
                            slate: "text-slate-700 bg-slate-100",
                            green: "text-green-700 bg-green-50",
                            cyan: "text-cyan-700 bg-cyan-50"
                        }[item.color] || "text-slate-700 bg-slate-50";

                        return (
                            <div key={item.type} className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg ${colorClass}`}>
                                <Icon className="w-3.5 h-3.5" />
                                <span>{item.label}</span>
                            </div>
                        );
                    });
                  })()}
               </div>

               {/* 3. Metadata Footer */}
               <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                     <div className="flex items-center gap-1 text-slate-500">
                        <FileText className="w-3.5 h-3.5" />
                        <span>{e.sources_count || 1} nguồn</span>
                     </div>

                  </div>
                  <span className="text-slate-400">{fmtDate(e.started_at)}</span>
               </div>
            </div>
          </a>
        ))}
      </div>

      {/* Pagination Controls */}
      {!loading && events.length > 0 && totalPages > 1 && (
        <div className="mt-8 flex justify-center items-center gap-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Trước
          </button>
          
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => {
              // Show first page, last page, current page, and pages around current
              const showPage = page === 1 || page === totalPages || 
                              Math.abs(page - currentPage) <= 1;
              
              if (!showPage) {
                // Show ellipsis
                if (page === 2 && currentPage > 3) {
                  return <span key={page} className="px-2 text-slate-400">...</span>;
                }
                if (page === totalPages - 1 && currentPage < totalPages - 2) {
                  return <span key={page} className="px-2 text-slate-400">...</span>;
                }
                return null;
              }
              
              return (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                    page === currentPage
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {page}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Tiếp
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && events.length === 0 && !error && (
        <div className="py-20 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-300">
            <div className="inline-flex justify-center items-center w-16 h-16 rounded-full bg-white border border-slate-200 mb-4 shadow-sm">
                <Filter className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-slate-900 font-medium mb-1">Không tìm thấy sự kiện nào</h3>
            <p className="text-slate-500 text-sm">Vui lòng thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.</p>
            {hasFilters && (
                <button 
                    onClick={clearFilters}
                    className="mt-4 text-blue-600 hover:text-blue-800 text-sm font-medium hover:underline"
                >
                    Xóa tất cả bộ lọc
                </button>
            )}
        </div>
      )}
    </div>
  );
}
