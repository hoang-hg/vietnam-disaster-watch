import { useEffect, useState, useMemo } from "react";
import { getJson } from "../api";
import VietnamMap from "../components/VietnamMap";
import { Filter, Calendar, Layers } from "lucide-react";
import { THEME_COLORS } from "../theme";
import VIETNAM_LOCATIONS from "../data/vietnam_locations.json";
import logoIge from "../assets/logo_ige.png";

// Build province lookup map
const PROVINCE_COORDS = {};
VIETNAM_LOCATIONS.forEach(loc => {
  if (loc.properties.category === "provincial_unit") {
    const [lon, lat] = loc.geometry.coordinates;
    PROVINCE_COORDS[loc.properties.name] = { lat, lon };
  }
});

const LEGEND_ITEMS = [
    { key: "storm", color: THEME_COLORS.storm, label: "Bão / Áp thấp" },
    { key: "flood_landslide", color: THEME_COLORS.flood_landslide, label: "Lũ / Sạt lở" },
    { key: "heat_drought", color: THEME_COLORS.heat_drought, label: "Nắng nóng / Hạn" },
    { key: "wind_fog", color: THEME_COLORS.wind_fog, label: "Gió mạnh / Sương mù" },
    { key: "storm_surge", color: THEME_COLORS.storm_surge, label: "Nước dâng" },
    { key: "extreme_other", color: THEME_COLORS.extreme_other, label: "Cực đoan khác" },
    { key: "wildfire", color: THEME_COLORS.wildfire, label: "Cháy rừng" },
    { key: "quake_tsunami", color: THEME_COLORS.quake_tsunami, label: "Động đất" },
];

export default function MapPage() {
  const [dataEvents, setDataEvents] = useState([]); // Raw data from API
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [activeFilters, setActiveFilters] = useState(() => LEGEND_ITEMS.map(i => i.key));

  // Fetch Data
  useEffect(() => {
    (async () => {
        setLoading(true);
        try {
            let query = `/api/events?limit=1000`;
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;
            
            const evs = await getJson(query);
            
            // Enrich events with coordinates from province if missing
            const enrichedEvents = evs.map(e => {
              if (e.lat && e.lon) return e;
              if (e.province && PROVINCE_COORDS[e.province]) {
                return {
                  ...e,
                  lat: PROVINCE_COORDS[e.province].lat,
                  lon: PROVINCE_COORDS[e.province].lon
                };
              }
              return e; // will be filtered out next step if still no coords
            });

            // Keep valid ones
            setDataEvents(enrichedEvents.filter(e => e.lat && e.lon));
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    })();
  }, [startDate, endDate]);

  // Derived state for display
  const displayedEvents = useMemo(() => {
    return dataEvents.filter(e => activeFilters.includes(e.disaster_type));
  }, [dataEvents, activeFilters]);

  const toggleFilter = (key) => {
    setActiveFilters(prev => 
        prev.includes(key) 
            ? prev.filter(k => k !== key) 
            : [...prev, key]
    );
  };

  return (
    <div className="flex flex-col flex-1 w-full bg-slate-100 font-sans h-full">
        
        {/* TOP CONTROL PANEL (Blended with background) */}
        <div className="flex-none bg-slate-100 z-10 p-2">
            <div className="max-w-5xl mx-auto flex flex-col gap-2">
                
                {/* Row 1: Title & Date (Compact) */}
                <div className="flex items-center justify-between">
                     <div className="flex items-center gap-3 text-blue-900 font-black text-sm uppercase tracking-tight">
                        <img 
                            src={logoIge} 
                            alt="IGE Logo" 
                            className="w-10 h-10 object-contain" 
                            style={{ mixBlendMode: 'multiply' }}
                        />
                        <Layers className="w-4 h-4 ml-1" />
                        <span>BẢN ĐỒ TỔNG HỢP RỦI RO THIÊN TAI</span>
                     </div>
                     
                     <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
                        <Calendar className="w-4 h-4 text-blue-500" />
                        <div className="flex items-center gap-1">
                            <input 
                                type="date"
                                value={startDate} 
                                onChange={(e) => setStartDate(e.target.value)}
                                className="bg-transparent border-none text-xs font-semibold text-slate-700 focus:ring-0 p-0 w-[115px]"
                            />
                            {endDate && <span className="text-slate-400 font-bold px-0.5">→</span>}
                            <input 
                                type="date"
                                placeholder="Đến ngày"
                                value={endDate} 
                                onChange={(e) => setEndDate(e.target.value)}
                                className="bg-transparent border-none text-xs font-semibold text-slate-700 focus:ring-0 p-0 w-[115px]"
                            />
                        </div>
                    </div>
                </div>

                {/* Row 2: Filters (Simple Pill Style) */}
                <div className="flex flex-wrap items-center gap-2">
                    {LEGEND_ITEMS.map((item) => {
                        const isActive = activeFilters.includes(item.key);
                        return (
                            <button
                                key={item.key}
                                onClick={() => toggleFilter(item.key)}
                                className={`
                                    flex items-center gap-1.5 px-2 py-1 rounded border text-xs transition-all duration-200 shadow-sm
                                    ${isActive 
                                        ? 'bg-blue-50 border-blue-600 text-blue-700 font-bold shadow-sm' 
                                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                                    }
                                `}
                            >
                                <span 
                                    className="w-2 h-2 rounded-full shadow-sm"
                                    style={{ backgroundColor: item.color }}
                                ></span>
                                {item.label}
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>

        {/* MAP AREA (Fills remaining space, centered and narrower) */}
        <div className="flex-1 w-full max-w-5xl mx-auto relative z-0">
             {loading && (
                <div className="absolute inset-0 z-[500] bg-white/50 flex items-center justify-center pointer-events-none">
                    <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full shadow-xl"></div>
                </div>
             )}
             <VietnamMap points={displayedEvents} />
        </div>
    </div>
  );
}
