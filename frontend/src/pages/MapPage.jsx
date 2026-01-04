import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { getJson } from "../api";
import VietnamMap from "../components/VietnamMap";
import { Filter, Calendar, Layers } from "lucide-react";
import { THEME_COLORS } from "../theme";
import VIETNAM_LOCATIONS from "../data/vietnam_locations.json";
import logoIge from "../assets/logo_ige.png";

// Build province lookup map
const getProvCoords = (name) => {
  // Try standardized centroids first (from provinces.js)
  if (window.__PROVINCE_CENTROIDS__ && window.__PROVINCE_CENTROIDS__[name]) {
    const [lat, lon] = window.__PROVINCE_CENTROIDS__[name];
    return { lat, lon };
  }
  
  // Fallback to static geojson
  const match = VIETNAM_LOCATIONS.find(loc => 
    loc.properties.category === "provincial_unit" && 
    (loc.properties.name === name || name.includes(loc.properties.name))
  );
  if (match) {
    const [lon, lat] = match.geometry.coordinates;
    return { lat, lon };
  }
  return null;
};

const LEGEND_ITEMS = [
    { key: "all", color: THEME_COLORS.brand, label: "Tất cả" },
    { key: "storm", color: THEME_COLORS.storm, label: "Bão / Áp thấp" },
    { key: "flood_landslide", color: THEME_COLORS.landslide, label: "Lũ / Sạt lở" },
    { key: "heat_drought", color: THEME_COLORS.drought, label: "Nắng nóng / Hạn" },
    { key: "wind_fog", color: THEME_COLORS.cold_surge, label: "Gió mạnh / Sương mù" },
    { key: "storm_surge", color: THEME_COLORS.storm_surge, label: "Nước dâng" },
    { key: "extreme_other", color: THEME_COLORS.extreme_weather, label: "Cực đoan khác" },
    { key: "wildfire", color: THEME_COLORS.wildfire, label: "Cháy rừng" },
    { key: "erosion", color: THEME_COLORS.erosion, label: "Xói lở" },
    { key: "quake_tsunami", color: THEME_COLORS.earthquake, label: "Động đất" },
    { key: "warning_forecast", color: THEME_COLORS.warning_forecast, label: "Tin cảnh báo" },
    { key: "recovery", color: THEME_COLORS.recovery, label: "Khắc phục hậu quả" },
];

export default function MapPage() {
  const [dataEvents, setDataEvents] = useState([]); // Raw data from API
  const [loading, setLoading] = useState(true);
  
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Filters
  const [startDate, setStartDate] = useState(() => {
    return searchParams.get("start_date") || (() => {
        const d = new Date();
        d.setDate(d.getDate() - 7);
        return d.toISOString().split('T')[0];
    })();
  });
  const [endDate, setEndDate] = useState(searchParams.get("end_date") || '');
  const [activeFilter, setActiveFilter] = useState(searchParams.get("type") || "all");
  
  const mid = Math.ceil(LEGEND_ITEMS.length / 2);
  const row1 = LEGEND_ITEMS.slice(0, mid);
  const row2 = LEGEND_ITEMS.slice(mid);

  // Fetch Data
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
        setLoading(true);
        try {
            let query = `/api/events?limit=1000`;
            if (startDate) query += `&start_date=${startDate}`;
            if (endDate) query += `&end_date=${endDate}`;
            
            const evs = await getJson(query, { signal: controller.signal });
            if (controller.signal.aborted) return;
            
            // Enrich events with coordinates from province if missing
            const enrichedEvents = evs.map(e => {
              if (e.lat && e.lon) return e;
              const coords = getProvCoords(e.province);
              if (coords) {
                return {
                  ...e,
                  lat: coords.lat,
                  lon: coords.lon
                };
              }
              return e; // will be filtered out next step if still no coords
            });

            // Keep valid ones
            setDataEvents(enrichedEvents.filter(e => e.lat != null && e.lon != null));
            
            // Sync to URL
            const newParams = {};
            if (activeFilter !== "all") newParams.type = activeFilter;
            if (startDate) newParams.start_date = startDate;
            if (endDate) newParams.end_date = endDate;
            
            const currentParams = Object.fromEntries(searchParams.entries());
            const isDifferent = Object.keys(newParams).length !== Object.keys(currentParams).length || 
                              Object.keys(newParams).some(k => String(newParams[k]) !== String(currentParams[k]));
            
            if (isDifferent) {
                setSearchParams(newParams, { replace: true });
            }
        } catch (e) {
            if (e.name === 'AbortError') return;
            console.error(e);
        } finally {
            setLoading(false);
        }
    })();

    return () => controller.abort();
  }, [startDate, endDate, activeFilter]);

  // Handle URL changes (Back button)
  useEffect(() => {
    const urlType = searchParams.get("type") || "all";
    const urlStart = searchParams.get("start_date") || (() => {
        const d = new Date();
        d.setDate(d.getDate() - 7);
        return d.toISOString().split('T')[0];
    })();
    const urlEnd = searchParams.get("end_date") || "";

    if (urlType !== activeFilter) setActiveFilter(urlType);
    if (urlStart !== startDate) setStartDate(urlStart);
    if (urlEnd !== endDate) setEndDate(urlEnd);
  }, [searchParams]);

  // Derived state for display
  const displayedEvents = useMemo(() => {
    const MAPPING = {
        storm: ['storm'],
        flood_landslide: ['flood', 'flash_flood', 'landslide', 'subsidence'],
        heat_drought: ['heatwave', 'drought', 'salinity'],
        wind_fog: ['cold_surge', 'wind_fog'],
        storm_surge: ['storm_surge'],
        extreme_other: ['extreme_weather', 'unknown'],
        wildfire: ['wildfire'],
        erosion: ['erosion'],
        quake_tsunami: ['earthquake', 'tsunami'],
        warning_forecast: ['warning_forecast'],
        recovery: ['recovery']
    };

    return dataEvents.filter(e => {
        if (activeFilter === "all") return true;
        const matchTypes = MAPPING[activeFilter] || [activeFilter];
        return matchTypes.includes(e.disaster_type);
    });
  }, [dataEvents, activeFilter]);

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

                {/* Filters (Symmetrical 2 rows of 5) */}
                <div className="flex flex-col gap-1.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                        {row1.map((item) => {
                            const isActive = activeFilter === item.key;
                            return (
                                <button
                                    key={item.key}
                                    onClick={() => setActiveFilter(item.key)}
                                    className={`
                                        flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[10px] uppercase font-black transition-all duration-200 shadow-sm whitespace-nowrap
                                        ${isActive 
                                            ? 'shadow-md scale-105 ring-1 ring-offset-1' 
                                            : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
                                        }
                                    `}
                                    style={isActive ? {
                                        backgroundColor: `${item.color}15`, 
                                        borderColor: item.color,
                                        color: item.color,
                                        boxShadow: `0 4px 6px -1px ${item.color}20`
                                    } : {}}
                                >
                                    <span 
                                        className="w-2.5 h-2.5 rounded-full shadow-inner"
                                        style={{ backgroundColor: item.color }}
                                    ></span>
                                    {item.label}
                                </button>
                            );
                        })}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                        {row2.map((item) => {
                            const isActive = activeFilter === item.key;
                            return (
                                <button
                                    key={item.key}
                                    onClick={() => setActiveFilter(item.key)}
                                    className={`
                                        flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[10px] uppercase font-black transition-all duration-200 shadow-sm whitespace-nowrap
                                        ${isActive 
                                            ? 'shadow-md scale-105 ring-1 ring-offset-1' 
                                            : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300'
                                        }
                                    `}
                                    style={isActive ? {
                                        backgroundColor: `${item.color}15`, 
                                        borderColor: item.color,
                                        color: item.color,
                                        boxShadow: `0 4px 6px -1px ${item.color}20`
                                    } : {}}
                                >
                                    <span 
                                        className="w-2.5 h-2.5 rounded-full shadow-inner"
                                        style={{ backgroundColor: item.color }}
                                    ></span>
                                    {item.label}
                                </button>
                            );
                        })}
                    </div>
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
