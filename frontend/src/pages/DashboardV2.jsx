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
  LabelList,
  LineChart,
  Line,
  PieChart,
  Pie,
  Legend
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
import { Helmet } from "react-helmet-async";

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
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString('vi-VN'));

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
      setLastUpdated(new Date().toLocaleTimeString('vi-VN'));
    } catch (e) {
      setError(e.message || "Load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 300_000); // Tự động cập nhật mỗi 5 phút
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

  // [NEW] Impact Trend Calculation
  const impactTrendData = useMemo(() => {
    const daily = {};
    events.forEach(e => {
        const date = new Date(e.started_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
        if (!daily[date]) daily[date] = { date, deaths: 0, missing: 0, injured: 0 };
        daily[date].deaths += (e.deaths || 0);
        daily[date].missing += (e.missing || 0);
        daily[date].injured += (e.injured || 0);
    });
    // Sort by date (naive string match works for display if data is chronological)
    return Object.values(daily).slice(-15); // Show last 15 days of data
  }, [events]);

  const isDark = document.documentElement.classList.contains('dark');

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Viet Disaster Watch | Hệ thống theo dõi rủi ro thiên tai</title>
        <meta name="description" content="Hệ thống tổng hợp và cảnh báo thiên tai sớm từ các cơ quan chính thống tại Việt Nam." />
        <meta property="og:title" content="Viet Disaster Watch - Theo dõi thiên tai thời gian thực" />
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

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight animate-in fade-in slide-in-from-left duration-700">Tổng quan</h1>
          <p className="text-slate-500 text-xs mt-1 flex items-center gap-2">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            Dữ liệu cập nhật: {lastUpdated} 
            <span className="bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded text-[9px] font-bold border border-emerald-100 uppercase tracking-tighter">
              Tự động (5 ph)
            </span>
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
                  <option value="warning_forecast">Cảnh báo, dự báo</option>
                  <option value="recovery">Khắc phục hậu quả</option>
              </select>
              <Filter className="w-3 h-3 text-slate-400 dark:text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

            <div 
              onClick={() => dateInputRef.current?.showPicker()}
              className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-1.5 shadow-sm relative group hover:border-blue-300 dark:hover:border-blue-500 transition-all cursor-pointer min-w-[140px] justify-center"
            >
              <span className="text-sm font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
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

      {/* [NEW] ANALYTICS INSIGHT SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in zoom-in duration-1000">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-red-500" /> Biểu đồ thương vong (Xu hướng)
                </h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={impactTrendData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" className="opacity-50 dark:opacity-10" />
                    <XAxis dataKey="date" tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} />
                    <YAxis tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', backgroundColor: isDark ? '#1e293b' : '#fff' }}
                      itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                    <Line type="monotone" dataKey="deaths" name="Tử vong" stroke="#ef4444" strokeWidth={3} dot={{ r: 4, fill: '#ef4444' }} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="missing" name="Mất tích" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="injured" name="Bị thương" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-6">
              <h3 className="font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" /> Tỉ lệ loại hình thiên tai
              </h3>
              <div className="h-64 flex items-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData.filter(d => d.count > 0)}
                      cx="40%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="count"
                      nameKey="name"
                      isAnimationActive={true}
                    >
                      {chartData.filter(d => d.count > 0).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip 
                       contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', backgroundColor: isDark ? '#1e293b' : '#fff' }}
                    />
                    <Legend 
                       layout="vertical" 
                       align="right" 
                       verticalAlign="middle" 
                       iconType="circle"
                       wrapperStyle={{ fontSize: '11px', paddingLeft: '20px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
          </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col h-full transition-all duration-300">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-white dark:bg-slate-900">
              <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" /> Danh sách sự kiện
              </h3>
              <Link to="/events" className="text-xs flex items-center gap-1 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors">
                Xem tất cả <ArrowRight className="w-3 h-3" />
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
                        <Badge tone={TYPE_TONES[e.disaster_type] || "slate"} className="w-fit px-1.5 py-0.5 text-[8px] mb-2">
                           {fmtType(e.disaster_type)}
                        </Badge>
                        <h5 className="font-bold text-slate-900 dark:text-white text-[11px] leading-tight line-clamp-2 group-hover/fav:text-blue-600 transition-colors">{e.title}</h5>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-2">{fmtTimeAgo(e.last_updated_at)}</span>
                     </Link>
                   ))}
                </div>
              </div>
            )}

            <div className="divide-y divide-slate-100 dark:divide-slate-800 flex-1 min-h-[1050px]">
              {events.slice(page * 10, (page + 1) * 10).map((event) => (
                <div key={event.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all group relative border-l-4 border-transparent hover:border-blue-500/30">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <Badge tone={TYPE_TONES[event.disaster_type] || "slate"} className="px-1.5 py-0.5 text-[9px] uppercase font-black">
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
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3 text-slate-400" /> {event.province}</span>
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3 text-slate-400" /> {new Date(event.started_at).toLocaleDateString('vi-VN')}</span>
                  </div>
                </div>
              ))}
              {events.length === 0 && <div className="p-8 text-center text-slate-500 dark:text-slate-400 text-sm">Chưa có dữ liệu sự kiện</div>}
            </div>

            {/* Pagination Controls - Fixed at Bottom */}
            {events.length > 0 && (
              <div className="mt-auto p-4 border-t border-slate-100 flex justify-center items-center gap-2 bg-slate-50/30">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                          className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${
                            i === currentPage
                              ? 'bg-blue-600 text-white shadow-md scale-110 z-10'
                              : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
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
                  className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Tiếp
                </button>
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
              {riskiestHotspots?.slice(0, 15).map((p, idx) => {
                const isActive = provQuery === p.province;
                return (
                  <button 
                    key={p.province} 
                    onClick={() => setProvQuery(isActive ? "" : p.province)}
                    className={`w-full flex items-center justify-between py-1.5 px-2 rounded-lg transition-all ${
                      isActive 
                        ? "bg-blue-50 dark:bg-blue-900/40 border border-blue-100 dark:border-blue-800 shadow-sm" 
                        : "hover:bg-slate-50 dark:hover:bg-slate-800 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${
                        isActive ? "bg-blue-600 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                      }`}>{idx + 1}</span>
                      <span className={`text-sm font-medium ${isActive ? "text-blue-700 dark:text-blue-300" : "text-slate-700 dark:text-slate-300"}`}>{p.province}</span>
                    </div>
                    <div className="text-right">
                      <span className={`font-bold text-sm ${isActive ? "text-blue-900 dark:text-blue-100" : "text-slate-900 dark:text-slate-100"}`}>{p.events}</span>
                      <span className={`text-[10px] ml-1 ${isActive ? "text-blue-500 dark:text-blue-400" : "text-slate-500 dark:text-slate-500"}`}>vụ</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 transition-all duration-300">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Phân loại thiên tai</h3>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 30 }} barCategoryGap="15%">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" className="dark:opacity-10" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip 
                    cursor={{fill: '#f1f5f9', opacity: 0.1}} 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', backgroundColor: isDark ? '#1e293b' : '#fff', color: isDark ? '#fff' : '#000' }}
                  />
                  <Bar 
                    dataKey="count" 
                    radius={[0, 4, 4, 0]} 
                    barSize={24}
                    isAnimationActive={true}
                    animationDuration={1500}
                    animationBegin={200}
                  >
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
