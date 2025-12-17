import { useEffect, useState } from "react";
import { getJson } from "../api";
import VietnamMap from "../components/VietnamMap";
import { Filter, Layers } from "lucide-react";
import { THEME_COLORS } from "../theme";

export default function MapPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  // Default to showing events from the last 7 days to avoid clutter
  // Default to today
  const [startDate, setStartDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    (async () => {
        setLoading(true);
        try {
            let query = `/api/events?limit=1000`;
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;
            
            const evs = await getJson(query);
            // Filter only events with coordinates and exclude 'unknown' type
            setEvents(evs.filter(e => e.lat && e.lon && e.disaster_type !== 'unknown'));
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    })();
  }, [startDate, endDate]);

  const LEGEND_ITEMS = [
    { key: "storm", color: THEME_COLORS.storm, label: "Bão / Áp thấp" },
    { key: "flood_landslide", color: THEME_COLORS.flood_landslide, label: "Mưa lũ / Sạt lở" },
    { key: "heat_drought", color: THEME_COLORS.heat_drought, label: "Nắng nóng / Hạn" },
    { key: "wind_fog", color: THEME_COLORS.wind_fog, label: "Gió mạnh / Sương mù" },
    { key: "storm_surge", color: THEME_COLORS.storm_surge, label: "Nước dâng" },
    { key: "extreme_other", color: THEME_COLORS.extreme_other, label: "Cực đoan khác" },
    { key: "wildfire", color: THEME_COLORS.wildfire, label: "Cháy rừng" },
    { key: "quake_tsunami", color: THEME_COLORS.quake_tsunami, label: "Động đất / Sóng thần" },
  ];

  return (
    <div className="relative h-[calc(100vh-64px-40px)] w-full flex flex-col gap-4">
        {/* Top Control Bar (Outside the Map) */}
        <div className="bg-white p-3 rounded-xl shadow-sm border border-slate-200 flex flex-col gap-3 mx-4 mt-4">
            
            {/* Row 1: Title & Filters Group */}
            <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-4">
                    <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                        <Layers className="w-4 h-4 text-blue-600" />
                        Bản đồ rủi ro
                    </h2>
                    
                    <div className="flex items-center gap-2 border-l border-slate-200 pl-4">
                        <div className="flex items-center gap-2">
                             <input 
                                type="date"
                                value={startDate} 
                                onChange={(e) => setStartDate(e.target.value)}
                                className="text-xs border-slate-300 rounded focus:ring-blue-500 focus:border-blue-500 py-1 px-2 h-8 bg-slate-50"
                                title="Ngày bắt đầu"
                            />
                            <span className="text-slate-400">-</span>
                            <input 
                                type="date"
                                value={endDate} 
                                onChange={(e) => setEndDate(e.target.value)}
                                className="text-xs border-slate-300 rounded focus:ring-blue-500 focus:border-blue-500 py-1 px-2 h-8 bg-slate-50"
                                title="Ngày kết thúc"
                            />
                        </div>
                    </div>
                </div>

                <div className="text-xs text-slate-500">
                    Hiển thị <strong>{events.length}</strong> sự kiện
                </div>
            </div>

            {/* Row 2: Horizontal Legend (Grid on small screens, Flex on large) */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-100 pt-2">
                {LEGEND_ITEMS.map((item) => (
                    <div key={item.key} className="flex items-center gap-2 cursor-help" title={item.label}>
                        <span className="flex-none w-2.5 h-2.5 rounded-full ring-2 ring-white shadow-sm" style={{ backgroundColor: item.color }}></span>
                        <span className="text-xs font-medium text-slate-600 whitespace-nowrap">{item.label}</span>
                    </div>
                ))}
            </div>
        </div>

        {/* Loading Indicator */}
        {loading && (
            <div className="absolute inset-0 z-[500] bg-white/50 flex items-center justify-center pointer-events-none">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full shadow-xl"></div>
            </div>
        )}

        <div className="flex-1 w-full relative z-0">
             <VietnamMap points={events} />
        </div>
    </div>
  );
}
