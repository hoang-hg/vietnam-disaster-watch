import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getJson, fmtType, fmtDate, fmtTimeAgo } from "../api.js";
import { THEME_COLORS, CHART_COLORS } from "../theme.js";
import StatCard from "../components/StatCard.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import VietnamMap from "../components/VietnamMap.jsx";
import {
  LineChart,
  Line,
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
  Search
} from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [riskiest, setRiskiest] = useState(null);
  const [rawEvents, setRawEvents] = useState([]);
  const [articles, setArticles] = useState([]);
  const [hours, setHours] = useState(24);
  const [minRisk, setMinRisk] = useState(0);
  const [hazardType, setHazardType] = useState("all");
  const [provQuery, setProvQuery] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const events = useMemo(() => {
    let list = rawEvents;
    if (minRisk > 0) list = list.filter(e => e.risk_level >= minRisk);
    if (hazardType !== "all") list = list.filter(e => e.disaster_type === hazardType);
    if (provQuery) {
        const q = provQuery.toLowerCase();
        list = list.filter(e => e.province && e.province.toLowerCase().includes(q));
    }
    return list;
  }, [rawEvents, minRisk, hazardType, provQuery]);

  useEffect(() => {
    setPage(0);
  }, [minRisk, hours, hazardType, provQuery]);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const [s, riskData, evs, arts] = await Promise.all([
        getJson(`/api/stats/summary?hours=${hours}`),
        getJson(`/api/stats/heatmap?hours=${hours}`),
        getJson(`/api/events?limit=50`),
        getJson(`/api/articles/latest?limit=20`)
      ]);
      setStats(s);
      setRiskiest(riskData?.data || []);
      setRawEvents(evs.filter((e) => e.disaster_type && e.disaster_type !== "unknown"));
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
  }, [hours]);

  const mapPoints = useMemo(
    () =>
      events.map((e) => {
        let lat = e.lat;
        let lng = e.lng;

        // Fallback to province centroid if coordinates are missing/invalid
        if ((!lat || !lng) && e.province && window.__PROVINCE_CENTROIDS__) {
            const centroid = window.__PROVINCE_CENTROIDS__[e.province];
            if (centroid) {
                [lat, lng] = centroid;
            }
        }
        
        return {
            id: e.id,
            title: e.title,
            lat: lat,
            lng: lng,
            risk_level: e.risk_level,
            type: e.disaster_type,
        };
      }),
    [events]
  );

  const chartData = useMemo(() => {
    // 1. Initialize all 8 groups with 0
    const agg = {
      storm: 0,
      flood_landslide: 0,
      heat_drought: 0,
      wind_fog: 0,
      storm_surge: 0,
      extreme_other: 0,
      wildfire: 0,
      quake_tsunami: 0,
    };
    
    // 2. Legacy Map
    const MAP = {
        flood: 'flood_landslide',
        landslide: 'flood_landslide',
        heavy_rain: 'flood_landslide',
        earthquake: 'quake_tsunami',
        tsunami: 'quake_tsunami',
        wind_hail: 'extreme_other',
        extreme_weather: 'heat_drought',
    };
    
    // 3. Aggregate
    events.forEach((e) => {
        const key = MAP[e.disaster_type] || e.disaster_type;
        if (agg[key] !== undefined) {
            agg[key]++;
        } else {
             // fallback for truly unknown types if any
             // agg[key] = 1; 
        }
    });
    
    // 4. Transform to array & Sort
    return Object.entries(agg)
        .map(([k, v]) => ({ 
            name: k, 
            count: v,
            fill: THEME_COLORS[k] || THEME_COLORS.unknown
        }))
        // Sort by count desc, then by fixed order if needed to keep list stable? 
        // User wants to see all 8, maybe stable order is better than sorting by count 0?
        // Let's sort by count desc for now to highlight active ones.
        .sort((a, b) => b.count - a.count);
  }, [events]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tổng quan</h1>
          <p className="text-slate-500 text-sm mt-1">
            Cập nhật lần cuối: {new Date().toLocaleTimeString('vi-VN')}
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-2">
          
          {/* Province Search */}
          <div className="relative">
             <input
                type="text"
                placeholder="Tìm tỉnh..."
                value={provQuery}
                onChange={(e) => setProvQuery(e.target.value)}
                className="w-32 py-1.5 pl-8 pr-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-400"
             />
             <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Hazard Filter */}
          <div className="relative">
             <select
                 value={hazardType}
                 onChange={(e) => setHazardType(e.target.value)}
                 className="appearance-none bg-white border border-slate-200 text-slate-700 text-xs font-medium py-1.5 pl-3 pr-8 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer max-w-[120px] truncate"
             >
                 <option value="all">Mọi thiên tai</option>
                 <option value="storm">Bão / ATNĐ</option>
                 <option value="flood_landslide">Mưa / Lũ / Sạt lở</option>
                 <option value="heat_drought">Nắng nóng / Hạn</option>
                 <option value="wind_fog">Gió / Sương mù</option>
                 <option value="storm_surge">Nước dâng</option>
                 <option value="quake_tsunami">Động đất / Sóng thần</option>
                 <option value="wildfire">Cháy rừng</option>
                 <option value="extreme_other">Khác</option>
             </select>
             <Filter className="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Risk Filter */}
          <div className="relative">
             <select
                 value={minRisk}
                 onChange={(e) => setMinRisk(Number(e.target.value))}
                 className="appearance-none bg-white border border-slate-200 text-slate-700 text-xs font-medium py-1.5 pl-3 pr-8 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
             >
                 <option value={0}>Mọi rủi ro</option>
                 <option value={1}>Cấp 1+</option>
                 <option value={2}>Cấp 2+</option>
                 <option value={3}>Cấp 3+</option>
                 <option value={4}>Cấp 4+</option>
                 <option value={5}>Cấp 5</option>
             </select>
             <Filter className="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-1 flex items-center shadow-sm">
            {[24, 48, 72].map((h) => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  hours === h
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
          <button
            onClick={load}
            className="p-2 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 hover:text-slate-900 shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Sự kiện mới"
          value={stats?.events_24h || 0}
          sub="Trong 24h qua"
          icon={AlertTriangle}
          trend={stats?.events_24h > 0 ? "up" : "neutral"}
          color="text-red-600"
        />
        <StatCard
          title="Tỉnh thành ảnh hưởng"
          value={riskiest ? riskiest.length : 0}
          sub="Vùng nguy cơ"
          icon={MapPin}
          trend="neutral"
          color="text-orange-600"
        />
        <StatCard
          title="Bài viết thu thập"
          value={stats?.articles_24h || 0}
          sub="Từ 38 nguồn tin tức"
          icon={Activity}
          trend="up"
          color="text-blue-600"
        />
        <StatCard
          title="Mức rủi ro cao nhất"
          value={rawEvents.length > 0 ? `Cấp ${Math.max(...rawEvents.map(e => e.risk_level || 0), 0)}` : "Chưa có"} 
          sub="Đánh giá rủi ro"
          icon={TrendingUp}
          color="text-purple-600"
        />
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Map & Risky Provinces (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recent Events Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" />
                Danh sách sự kiện
              </h3>
              <Link to="/events" className="text-xs flex items-center gap-1 text-slate-500 hover:text-slate-900 transition-colors">
                Xem tất cả <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="divide-y divide-slate-100 flex-1">
              {events.slice(page * 10, (page + 1) * 10).map((event) => (
                <div key={event.id} className="p-4 hover:bg-slate-50 transition-colors group">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block w-2 h-2 rounded-full`} style={{ backgroundColor: THEME_COLORS[event.disaster_type] || THEME_COLORS.unknown }}></span>
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        {fmtType(event.disaster_type)}
                      </span>
                    </div>
                    <RiskBadge level={event.risk_level} />
                  </div>
                  <Link to={`/events/${event.id}`} className="block">
                    <h4 className="font-medium text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1 mb-1">
                      {event.title}
                    </h4>
                  </Link>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {event.province}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> {fmtDate(event.started_at)}
                    </span>
                  </div>
                </div>
              ))}
              {events.length === 0 && (
                <div className="p-8 text-center text-slate-500 text-sm">
                  Chưa có dữ liệu sự kiện gần đây
                </div>
              )}
            </div>
            {/* Pagination Controls */}
            {events.length > 10 && (
              <div className="p-3 border-t border-slate-100 flex justify-between items-center bg-slate-50/50">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1 text-xs font-medium rounded-md border border-slate-200 bg-white text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
                >
                  Trước
                </button>
                <span className="text-xs text-slate-500">
                  Trang {page + 1} / {Math.ceil(events.length / 10)}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(Math.ceil(events.length / 10) - 1, p + 1))}
                  disabled={page >= Math.ceil(events.length / 10) - 1}
                  className="px-3 py-1 text-xs font-medium rounded-md border border-slate-200 bg-white text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
                >
                  Sau
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Charts & Feeds (1/3 width) */}
        <div className="space-y-6">
          
          {/* Top Risky Provinces */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              Điểm nóng rủi ro
            </h3>
            <div className="space-y-3">
              {riskiest?.slice(0, 10).map((p, idx) => (
                <div key={p.province} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 text-slate-500 text-xs font-bold">
                      {idx + 1}
                    </span>
                    <span className="font-medium text-slate-700">{p.province}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-slate-900 text-lg">{p.events}</span>
                    <span className="text-xs text-slate-500 ml-1">vụ</span>
                  </div>
                </div>
              ))}
              {!riskiest || riskiest.length === 0 && (
                <div className="text-center text-slate-400 text-xs py-4">Không có dữ liệu</div>
              )}
            </div>
          </div>

          {/* Simple Type Distribution Chart */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="font-semibold text-slate-900 mb-4">Phân loại thiên tai</h3>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  data={chartData} 
                  layout="vertical" 
                  margin={{ left: 0, right: 30 }}
                  barCategoryGap="15%" // Add space between bars
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={100} tickFormatter={fmtType} tick={{ fontSize: 11 }} />
                  <Tooltip 
                    cursor={{fill: '#f1f5f9'}}
                    content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                            <div className="bg-white p-2 border border-slate-200 shadow-md rounded-lg text-xs">
                            <span className="font-semibold">{fmtType(data.name)}</span>: {data.count}
                            </div>
                        );
                        }
                        return null;
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={24}>
                    {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                    {/* Label at the end of bar */}
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
