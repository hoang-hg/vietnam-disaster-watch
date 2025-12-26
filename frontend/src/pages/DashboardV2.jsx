import { useEffect, useMemo, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { 
  getJson, 
  fmtType, 
  fmtDate, 
  fmtTimeAgo, 
  cleanText 
} from "../api.js";
import { THEME_COLORS } from "../theme.js";
import StatCard from "../components/StatCard.jsx";
import Badge from "../components/Badge.jsx";
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
  ArrowRight,
  Search,
  FileText,
  Bell
} from "lucide-react";

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

export default function Dashboard() {
  const dateInputRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [rawEvents, setRawEvents] = useState([]);
  const [articles, setArticles] = useState([]);
  
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState("");
  
  const [hazardType, setHazardType] = useState("all");
  const [provQuery, setProvQuery] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const handleStorage = () => {
      const storedUser = localStorage.getItem("user");
      if (storedUser) {
        try {
          const parsed = JSON.parse(storedUser);
          if (parsed && typeof parsed === 'object') {
              setUser(parsed);
          }
        } catch (e) {
          console.error("Dashboard session sync error:", e);
        }
      }
    };
    handleStorage();
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const favoriteProvince = user?.favorite_province;

  const VALID_PROVINCES = [
    "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên",
    "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh",
    "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình",
    "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế",
    "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa",
    "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp",
    "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
  ]; 
  /* Helper to normalize string for search */
  const normalizeStr = (str, removeSpaces = false) => {
    if (!str) return "";
    let res = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (removeSpaces) res = res.replace(/\s+/g, '');
    return res;
  }

  const events = useMemo(() => {
    let list = rawEvents;
    if (hazardType !== "all") list = list.filter(e => e.disaster_type === hazardType);
    if (provQuery) {
        const q = normalizeStr(provQuery, true);
        list = list.filter(e => e.province && normalizeStr(e.province, true).includes(q));
    }
    if (searchQuery) {
        const q = normalizeStr(searchQuery);
        list = list.filter(e => e.title && normalizeStr(e.title).includes(q));
    }
    if (quickFilter === "casualties") {
        list = list.filter(e => (e.deaths || 0) + (e.missing || 0) + (e.injured || 0) > 0);
    } else if (quickFilter === "damage") {
        list = list.filter(e => {
            const hasAmount = (e.damage_billion_vnd || 0) > 0;
            const det = e.details || {};
            return hasAmount || 
                   (det.homes?.length > 0) || 
                   (det.agriculture?.length > 0) || 
                   (det.infrastructure?.length > 0) || 
                   (det.marine?.length > 0) || 
                   (det.disruption?.length > 0) || 
                   (det.damage?.length > 0);
        });
    } else if (quickFilter === "provinces") {
        list = list.filter(e => e.province && VALID_PROVINCES.includes(e.province));
    }
    return list;
  }, [rawEvents, hazardType, provQuery, searchQuery, quickFilter]);

  useEffect(() => {
    setPage(0);
  }, [startDate, endDate, hazardType, provQuery, searchQuery, quickFilter]);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      let queryParams = `?start_date=${startDate}`;
      if (endDate) queryParams += `&end_date=${endDate}`;

      const [s, evs, arts] = await Promise.all([
        getJson(`/api/stats/summary${queryParams}`),
        getJson(`/api/events${queryParams}&limit=200`),
        getJson(`/api/articles/latest?limit=20`)
      ]);
      setStats(s);
      setRawEvents(evs.filter((e) => e.disaster_type && !["unknown", "other"].includes(e.disaster_type)));
      setArticles(arts);
    } catch (e) {
      setError(e.message || "Load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [startDate, endDate]);

  const isToday = startDate === new Date().toISOString().split('T')[0] && !endDate;

  const handleReset = () => {
    setStartDate(new Date().toISOString().split('T')[0]);
    setEndDate("");
    setProvQuery("");
    setSearchQuery("");
    setHazardType("all");
    setQuickFilter(null);
    setPage(0);
  };

  const mapPoints = useMemo(() => 
    events.map((e) => ({
      id: e.id,
      title: e.title,
      lat: e.lat,
      lng: e.lng || e.lon,
      disaster_type: e.disaster_type,
    })), [events]);

  const chartData = useMemo(() => {
    const agg = {
      storm: 0, flood: 0, flash_flood: 0, landslide: 0, subsidence: 0, 
      drought: 0, salinity: 0, extreme_weather: 0, heatwave: 0, cold_surge: 0,
      earthquake: 0, tsunami: 0, storm_surge: 0, wildfire: 0,
      warning_forecast: 0, recovery: 0
    };
    events.forEach((e) => {
        if (agg[e.disaster_type] !== undefined) agg[e.disaster_type]++;
    });
    return Object.entries(agg)
        .map(([k, v]) => ({ 
            name: fmtType(k), 
            count: v,
            fill: THEME_COLORS[k] || THEME_COLORS.unknown
        }))
        .sort((a, b) => b.count - a.count);
  }, [events]);

  const riskiestHotspots = useMemo(() => {
    const counts = {};
    events.forEach(e => {
        if (e.province && VALID_PROVINCES.includes(e.province)) {
            counts[e.province] = (counts[e.province] || 0) + 1;
        }
    });
    return Object.entries(counts)
        .map(([province, count]) => ({ province, events: count }))
        .sort((a, b) => b.events - a.events);
  }, [events]);

  const favoriteEvents = useMemo(() => {
    if (!favoriteProvince) return [];
    return rawEvents.filter(e => e.province === favoriteProvince).slice(0, 3);
  }, [rawEvents, favoriteProvince]);

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div className="text-sm font-medium">Lỗi tải dữ liệu: {error}</div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tổng quan</h1>
          <p className="text-slate-500 text-sm mt-1">
            Cập nhật: {new Date().toLocaleTimeString('vi-VN')}
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-2">
           <div className="relative">
              <input
                 type="text"
                 placeholder="Tìm theo tỉnh..."
                 value={provQuery}
                 onChange={(e) => setProvQuery(e.target.value)}
                 className="w-48 py-1.5 pl-8 pr-2 bg-white border border-slate-200 rounded-lg text-xs font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
           </div>

           <div className="relative">
              <input
                 type="text"
                 placeholder="Tìm tên sự kiện..."
                 value={searchQuery}
                 onChange={(e) => setSearchQuery(e.target.value)}
                 className="w-48 py-1.5 pl-8 pr-2 bg-white border border-slate-200 rounded-lg text-xs font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
           </div>

           <div className="relative">
              <select
                  value={hazardType}
                  onChange={(e) => setHazardType(e.target.value)}
                  className="appearance-none bg-white border border-slate-200 text-slate-700 text-xs font-medium py-1.5 pl-3 pr-8 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
              >
                  <option value="all">Tất cả thông tin</option>
                  <option value="storm">Bão, ATNĐ</option>
                  <option value="flood">Lũ lụt</option>
                  <option value="flash_flood">Lũ quét, Lũ ống</option>
                  <option value="landslide">Sạt lở đất, đá</option>
                  <option value="subsidence">Sụt lún đất</option>
                  <option value="drought">Hạn hán</option>
                  <option value="salinity">Xâm nhập mặn</option>
                  <option value="extreme_weather">Mưa lớn, Lốc, Sét, Mưa Đá</option>
                  <option value="heatwave">Nắng nóng</option>
                  <option value="cold_surge">Rét hại, Sương muối</option>
                  <option value="earthquake">Động đất</option>
                  <option value="tsunami">Sóng thần</option>
                  <option value="storm_surge">Nước dâng</option>
                  <option value="wildfire">Cháy rừng</option>
                  <option value="warning_forecast">Cảnh báo, dự báo</option>
                  <option value="recovery">Khắc phục hậu quả</option>
              </select>
              <Filter className="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
           </div>

            <div 
              onClick={() => dateInputRef.current?.showPicker()}
              className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-1.5 shadow-sm relative group hover:border-blue-300 transition-all cursor-pointer min-w-[140px] justify-center"
            >
              <span className="text-sm font-bold text-slate-700 whitespace-nowrap">
                 {startDate.split('-').reverse().join('/')}
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
                  className="absolute inset-0 opacity-0 -z-10 pointer-events-none"
              />
            </div>

           <button 
             onClick={handleReset}
             title="Đặt lại tất cả bộ lọc"
             className="p-2.5 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-500 transition-all shadow-sm group"
           >
             <RefreshCw className={`w-4 h-4 group-hover:rotate-180 transition-transform duration-500 ${loading ? 'animate-spin' : ''}`} />
           </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title={isToday ? "Sự kiện mới (24h)" : `Sự kiện ngày ${startDate}`}
          value={stats?.events_count || 0}
          sub={stats?.needs_verification_count ? `${stats.needs_verification_count} tin cần xác minh` : "Dữ liệu thời gian thực"}
          icon={Activity}
          trend={stats?.events_count > 0 ? "up" : "neutral"}
          color="text-blue-600"
          active={quickFilter === null}
          onClick={() => setQuickFilter(null)}
        />
        <StatCard
          title="Tỉnh thành ảnh hưởng"
          value={stats?.provinces_count || 0}
          sub="Ghi nhận trong kỳ"
          icon={MapPin}
          color="text-orange-600"
          active={quickFilter === "provinces"}
          onClick={() => setQuickFilter(quickFilter === "provinces" ? null : "provinces")}
        />
        <StatCard
          title="Sự kiện có thiệt hại người"
          value={stats?.events_with_human_damage || 0}
          sub="Số vụ ghi nhận thương vong"
          icon={AlertTriangle}
          color="text-red-500"
          active={quickFilter === "casualties"}
          onClick={() => setQuickFilter(quickFilter === "casualties" ? null : "casualties")}
        />
        <StatCard
          title="Sự kiện có thiệt hại tài sản"
          value={stats?.events_with_property_damage || 0}
          sub="Số vụ ghi nhận mất mát tài sản"
          icon={TrendingUp}
          color="text-emerald-500"
          active={quickFilter === "damage"}
          onClick={() => setQuickFilter(quickFilter === "damage" ? null : "damage")}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" /> Danh sách sự kiện
              </h3>
              <Link to="/events" className="text-xs flex items-center gap-1 text-slate-500 hover:text-slate-900">
                Xem tất cả <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            
            {/* Highlights for favorite area */}
            {favoriteProvince && favoriteEvents.length > 0 && (
              <div className="bg-blue-50/50 p-4 border-b border-blue-100">
                <div className="flex items-center gap-2 text-blue-700 font-bold text-xs uppercase tracking-wider mb-3">
                   <Bell className="w-3.5 h-3.5 animate-bounce" />
                   Thiên tai tại {favoriteProvince}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                   {favoriteEvents.map(e => (
                     <Link key={e.id} to={`/events/${e.id}`} className="bg-white p-3 rounded-xl border border-blue-200 shadow-sm hover:shadow-md transition-all flex flex-col">
                        <Badge tone={TYPE_TONES[e.disaster_type] || "slate"} className="w-fit px-1.5 py-0.5 text-[8px] mb-2">
                           {fmtType(e.disaster_type)}
                        </Badge>
                        <h5 className="font-bold text-slate-900 text-[11px] leading-tight line-clamp-2">{e.title}</h5>
                        <span className="text-[10px] text-slate-500 mt-2">{fmtTimeAgo(e.last_updated_at)}</span>
                     </Link>
                   ))}
                </div>
              </div>
            )}

            <div className="divide-y divide-slate-100 flex-1 min-h-[1050px]">
              {events.slice(page * 10, (page + 1) * 10).map((event) => (
                <div key={event.id} className="p-4 hover:bg-slate-50 transition-colors group relative border-l-4 border-transparent hover:border-blue-500/30">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <Badge tone={TYPE_TONES[event.disaster_type] || "slate"} className="px-1.5 py-0.5 text-[9px] uppercase font-black">
                        {fmtType(event.disaster_type)}
                      </Badge>
                    </div>
                  </div>
                  <Link to={`/events/${event.id}`}>
                    <h4 className="font-bold text-slate-930 group-hover:text-blue-600 transition-colors line-clamp-2 mb-2 text-sm leading-tight">
                      {cleanText(event.title)}
                    </h4>
                  </Link>
                  <div className="flex items-center gap-4 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {event.province}</span>
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(event.started_at).toLocaleDateString('vi-VN')}</span>
                  </div>
                </div>
              ))}
              {events.length === 0 && <div className="p-8 text-center text-slate-500 text-sm">Chưa có dữ liệu sự kiện</div>}
            </div>

            {/* Pagination Controls - Fixed at Bottom */}
            {events.length > 0 && (
              <div className="mt-auto p-4 border-t border-slate-100 flex justify-center items-center gap-2 bg-slate-50/30">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Trước
                </button>
                
                <div className="flex items-center gap-1">
                  {(() => {
                    const totalPages = Math.ceil(events.length / 10);
                    const currentPage = page + 1;
                    const items = [];
                    for (let i = 1; i <= totalPages; i++) {
                      const showPage = i === 1 || i === totalPages || Math.abs(i - currentPage) <= 1;
                      if (!showPage) {
                        if (i === 2 && currentPage > 3) {
                           items.push(<span key="d1" className="px-1 text-slate-400">...</span>);
                           i = currentPage - 2;
                        } else if (i === currentPage + 2 && i < totalPages) {
                           items.push(<span key="d2" className="px-1 text-slate-400">...</span>);
                           i = totalPages - 1;
                        }
                        continue;
                      }
                      items.push(
                        <button
                          key={i}
                          onClick={() => setPage(i - 1)}
                          className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                            i === currentPage
                              ? 'bg-blue-600 text-white shadow-sm'
                              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                          }`}
                        >
                          {i}
                        </button>
                      );
                    }
                    return items;
                  })()}
                </div>

                <button
                  onClick={() => setPage(p => Math.min(Math.ceil(events.length / 10) - 1, p + 1))}
                  disabled={page >= Math.ceil(events.length / 10) - 1}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Tiếp
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" /> Điểm nóng rủi ro
            </h3>
            <div className="space-y-1">
              {riskiestHotspots?.slice(0, 15).map((p, idx) => {
                const isActive = provQuery === p.province;
                return (
                  <button 
                    key={p.province} 
                    onClick={() => setProvQuery(isActive ? "" : p.province)}
                    className={`w-full flex items-center justify-between py-1.5 px-2 rounded-lg transition-all ${
                      isActive 
                        ? "bg-blue-50 border border-blue-100 shadow-sm" 
                        : "hover:bg-slate-50 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${
                        isActive ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500"
                      }`}>{idx + 1}</span>
                      <span className={`text-sm font-medium ${isActive ? "text-blue-700" : "text-slate-700"}`}>{p.province}</span>
                    </div>
                    <div className="text-right">
                      <span className={`font-bold text-sm ${isActive ? "text-blue-900" : "text-slate-900"}`}>{p.events}</span>
                      <span className={`text-[10px] ml-1 ${isActive ? "text-blue-500" : "text-slate-500"}`}>vụ</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-4">Phân loại thiên tai</h3>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 30 }} barCategoryGap="15%">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10 }} />
                  <Tooltip cursor={{fill: '#f1f5f9'}} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={24}>
                    {chartData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                    <LabelList dataKey="count" position="right" fontSize={12} fontWeight={600} fill="#64748b" /> 
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
