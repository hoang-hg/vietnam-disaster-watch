import { useEffect, useState, useMemo } from "react";
import {
  getJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import { MapPin, Clock, FileText, Zap, DollarSign, Users, Activity, Filter, X } from "lucide-react";
import VIETNAM_LOCATIONS from "../data/vietnam_locations.json";

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
const PROVINCES = VIETNAM_LOCATIONS
  .filter(f => f.properties.category === "provincial_unit")
  .map(f => f.properties.name)
  .sort();

export default function Events() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [province, setProvince] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params = new URLSearchParams();
        params.append("limit", "200");
        if (q) params.append("q", q);
        if (type) params.append("type", type);
        if (province) params.append("province", province);
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);

        const evs = await getJson(`/api/events?${params.toString()}`);
        
        // Filter out events classified as 'unknown' if not explicitly asked
        setEvents(
          evs.filter((e) => e.disaster_type && e.disaster_type !== "unknown")
        );
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
  };

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
                    <option value="storm">Bão / ATNĐ</option>
                    <option value="flood_landslide">Mưa lũ / Sạt lở</option>
                    <option value="heat_drought">Nắng nóng / Hạn hán</option>
                    <option value="wind_fog">Gió mạnh / Sương mù</option>
                    <option value="storm_surge">Nước dâng</option>
                    <option value="wildfire">Cháy rừng</option>
                    <option value="quake_tsunami">Động đất / Sóng thần</option>
                    <option value="extreme_other">Cực đoan khác</option>
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

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {events.map((e) => (
          <a
            key={e.id}
            href={`/events/${e.id}`}
            className="block group bg-white rounded-2xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all duration-300 flex flex-col overflow-hidden relative"
          >
            {/* Top Border Indicator for Impact/Severity Visual */}
            <div className={`h-1.5 w-full ${e.risk_level >= 4 ? 'bg-red-500' : (e.risk_level === 3 ? 'bg-orange-500' : 'bg-blue-500')}`}></div>
            
            <div className="p-5 flex flex-col h-full">
                {/* 1. Header: Province & Date */}
                <div className="flex justify-between items-start mb-3 text-xs text-slate-500 font-medium">
                    <span className="flex items-center gap-1 bg-slate-50 px-2 py-1 rounded">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        {e.province}
                    </span>
                    <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {fmtTimeAgo(e.last_updated_at)}
                    </span>
                </div>

                {/* 2. Title */}
                <h3 className="text-base font-bold text-slate-900 leading-snug mb-3 group-hover:text-blue-700 transition-colors line-clamp-2">
                    {e.title}
                </h3>

                {/* 3. Badges Row */}
                <div className="flex flex-wrap items-center gap-2 mb-4">
                    <Badge tone={TYPE_TONES[e.disaster_type] || "slate"}>
                       {fmtType(e.disaster_type)}
                    </Badge>
                    {e.risk_level && <RiskBadge level={e.risk_level} />}
                    <span className="text-xs text-slate-400 flex items-center gap-1 ml-auto">
                        <FileText className="w-3 h-3" /> {e.sources_count} tin
                    </span>
                </div>

                {/* 4. Impact Stats Grid (Auto layout) */}
                <div className="mt-auto pt-3 border-t border-slate-50 grid grid-cols-2 gap-2 text-xs">
                     {e.deaths ? (
                        <div className="flex items-center gap-1.5 text-red-700 font-medium">
                            <Users className="w-3.5 h-3.5" />
                            {e.deaths} tử vong
                        </div>
                     ) : null}
                     {e.damage_billion_vnd ? (
                        <div className="flex items-center gap-1.5 text-slate-700 font-medium col-span-2">
                            <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                            Thiệt hại: {fmtVndBillion(e.damage_billion_vnd)}
                        </div>
                     ) : null}
                     {(!e.deaths && !e.damage_billion_vnd) && (
                         <div className="col-span-2 text-slate-400 italic">
                            Chưa có thống kê thiệt hại
                         </div>
                     )}
                </div>
            </div>
          </a>
        ))}
      </div>

      {loading && (
          <div className="py-20 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-slate-500">Đang tải dữ liệu...</p>
          </div>
      )}

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
