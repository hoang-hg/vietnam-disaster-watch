import React, { useEffect, useState } from "react";
import { getJson, API_BASE } from "../api";
import { 
  Activity, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  RefreshCw,
  Search,
  Globe,
  Zap,
  ShieldCheck,
  LayoutDashboard,
  BarChart3,
  Server
} from "lucide-react";

export default function CrawlerDashboard() {
  const [statusData, setStatusData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // all, error, warning, success
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetchStatus(controller.signal);
    const interval = setInterval(() => fetchStatus(controller.signal), 30000); // 30s auto refresh
    return () => {
        controller.abort();
        clearInterval(interval);
    };
  }, []);

  async function fetchStatus(signal = null) {
    try {
      setLoading(true);
      const data = await getJson("/api/admin/crawler-status", { signal });
      if (signal?.aborted) return;
      setStatusData(data || []);
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const filteredData = statusData.filter(s => {
      const matchesFilter = filter === "all" || s.status === filter;
      const matchesSearch = s.source_name.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesFilter && matchesSearch;
  });

  const stats = {
      total: statusData.length,
      success: statusData.filter(s => s.status === 'success').length,
      warning: statusData.filter(s => s.status === 'warning').length,
      error: statusData.filter(s => s.status === 'error').length,
      avg_latency: statusData.length > 0 
        ? Math.round(statusData.reduce((acc, s) => acc + s.latency_ms, 0) / statusData.length) 
        : 0
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b1120] py-8 px-4 sm:px-6 lg:px-8 transition-colors duration-300">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
              <Server className="w-8 h-8 text-[#2fa1b3]" />
              GIÁM SÁT CRAWLER
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1 font-medium italic">
                Sức khỏe hệ thống thu thập dữ liệu thời gian thực
            </p>
          </div>
          
          <button 
            onClick={fetchStatus}
            className="flex items-center gap-2 px-6 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl font-black text-xs uppercase tracking-widest text-[#2fa1b3] hover:bg-slate-50 dark:hover:bg-slate-700 transition-all shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            LÀM MỚI
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            <StatCard label="TỔNG NGUỒN" value={stats.total} icon={<Globe className="w-5 h-5" />} color="blue" />
            <StatCard label="ỔN ĐỊNH" value={stats.success} icon={<CheckCircle className="w-5 h-5" />} color="green" />
            <StatCard label="DÙNG DỰ PHÒNG" value={stats.warning} icon={<AlertTriangle className="w-5 h-5" />} color="yellow" />
            <StatCard label="SỰ CỐ" value={stats.error} icon={<XCircle className="w-5 h-5" />} color="red" />
            <StatCard label="ĐỘ TRỄ TB" value={`${stats.avg_latency}ms`} icon={<Zap className="w-5 h-5" />} color="indigo" />
        </div>

        {/* Filter Section */}
        <div className="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm mb-6 flex flex-col md:flex-row gap-4 items-center">
            <div className="relative flex-grow">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                    type="text"
                    placeholder="Tìm kiếm nguồn tin..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm font-bold text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-[#2fa1b3]/20"
                />
            </div>
            
            <div className="flex p-1 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700">
                {['all', 'success', 'warning', 'error'].map(f => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                            filter === f 
                            ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm" 
                            : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                        }`}
                    >
                        {f === 'all' ? 'Tất cả' : f === 'success' ? 'Ổn định' : f === 'warning' ? 'Dự phòng' : 'Sự cố'}
                    </button>
                ))}
            </div>
        </div>

        {/* Status Table */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em]">Nguồn tin</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] text-center">Trạng thái</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em]">Phương thức dùng</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] text-center">Độ trễ</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] text-center">Tin mới</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em]">Cập nhật</th>
                            <th className="px-6 py-5 text-[10px] font-black uppercase text-slate-400 tracking-[0.2em]">Ghi chú</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                        {filteredData.map((s) => (
                            <tr key={s.source_name} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex flex-col">
                                        <span className="font-bold text-slate-800 dark:text-slate-100 text-sm italic">{s.source_name}</span>
                                        <span className="text-[10px] text-slate-400 font-medium font-mono">{s.source_name.toLowerCase().replace(/ /g, '.')}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex justify-center">
                                        <StatusBadge status={s.status} />
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-wrap gap-1">
                                        {(s.feed_used || "unknown").split(", ").map(f => (
                                            <span key={f} className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                                                f === 'primary_rss' ? 'bg-green-50 dark:bg-green-500/10 text-green-600 border-green-200 dark:border-green-500/20' :
                                                f === 'gnews' ? 'bg-yellow-50 dark:bg-yellow-500/10 text-yellow-600 border-yellow-200 dark:border-yellow-500/20' :
                                                f === 'html_scraper' ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 border-blue-200 dark:border-blue-500/20' :
                                                'bg-slate-50 dark:bg-slate-800 text-slate-400 border-slate-200 dark:border-slate-700'
                                            }`}>
                                                {f}
                                            </span>
                                        ))}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <span className={`text-xs font-black ${
                                            s.latency_ms > 5000 ? 'text-red-500' : 
                                            s.latency_ms > 2000 ? 'text-yellow-600' : 
                                            'text-slate-500 dark:text-slate-400'
                                        }`}>
                                        {s.latency_ms.toLocaleString()}ms
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-center">
                                     <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-black border border-slate-100 dark:border-slate-700">
                                        {s.articles_added}
                                     </span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
                                        <Clock className="w-3 h-3" />
                                        {new Date(s.last_run_at).toLocaleTimeString('vi-VN')}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className={`text-[10px] font-bold py-1 rounded max-w-[150px] truncate ${
                                        s.status === 'error' ? 'text-red-500' : 'text-slate-400'
                                    }`}>
                                        {s.last_error || '—'}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            
            {filteredData.length === 0 && !loading && (
                <div className="py-20 text-center">
                    <div className="w-16 h-16 bg-slate-50 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Search className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest text-xs">Không tìm thấy kết quả phù hợp</p>
                </div>
            )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }) {
    const colors = {
        blue: "bg-blue-600 shadow-blue-500/20",
        green: "bg-green-600 shadow-green-500/20",
        yellow: "bg-yellow-500 shadow-yellow-500/10",
        red: "bg-red-600 shadow-red-500/20",
        indigo: "bg-indigo-600 shadow-indigo-500/20"
    };
    
    return (
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between group hover:scale-[1.02] transition-transform">
            <div className={`w-10 h-10 rounded-xl ${colors[color]} flex items-center justify-center text-white mb-4 shadow-lg group-hover:rotate-12 transition-transform`}>
                {icon}
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">{label}</p>
                <p className="text-2xl font-black text-slate-800 dark:text-white mt-1 leading-none">{value}</p>
            </div>
        </div>
    );
}

function StatusBadge({ status }) {
    if (status === 'success') {
        return (
            <div className="flex items-center gap-2 bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-500 px-3 py-1 rounded-full border border-green-200 dark:border-green-500/20">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,1)]" />
                <span className="text-[10px] font-black uppercase tracking-widest">ỔN ĐỊNH</span>
            </div>
        );
    }
    if (status === 'warning') {
        return (
            <div className="flex items-center gap-2 bg-yellow-50 dark:bg-yellow-500/10 text-yellow-600 dark:text-yellow-500 px-3 py-1 rounded-full border border-yellow-200 dark:border-yellow-500/20">
                <div className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(234,179,8,1)]" />
                <span className="text-[10px] font-black uppercase tracking-widest">DỰ PHÒNG</span>
            </div>
        );
    }
    return (
        <div className="flex items-center gap-2 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-500 px-3 py-1 rounded-full border border-red-200 dark:border-red-500/20">
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-ping" />
            <span className="text-[10px] font-black uppercase tracking-widest">SỰ CỐ</span>
        </div>
    );
}
