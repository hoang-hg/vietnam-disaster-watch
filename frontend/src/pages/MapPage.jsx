import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { getJson } from "../api";
import VietnamMap from "../components/VietnamMap";
import DateFilter from "../components/DateFilter";
import { Filter, Calendar, Layers } from "lucide-react";
import { THEME_COLORS, DISASTER_METADATA } from "../theme";
import { PROVINCE_COORDINATES } from "../provinces";
import VIETNAM_LOCATIONS from "../data/vietnam_locations.json";
import logoIge from "../assets/logo_ige.png";

// Build optimized lookup map for province coordinates
// [OPTIMIZATION] Pre-compute lookup map to avoid O(N) search in loop
const PROVINCE_GEO_LOOKUP = {};
if (VIETNAM_LOCATIONS && Array.isArray(VIETNAM_LOCATIONS)) {
    VIETNAM_LOCATIONS.forEach(loc => {
        if (loc.properties?.category === "provincial_unit" && loc.properties?.name) {
            const [lon, lat] = loc.geometry.coordinates;
             // Store by lowercase name for lenient matching
            PROVINCE_GEO_LOOKUP[loc.properties.name.toLowerCase()] = { lat, lon };
        }
    });
}

const getProvCoords = (name) => {
  if (!name) return null;
  // 1. Try standardized centroids first (fastest)
  if (PROVINCE_COORDINATES && PROVINCE_COORDINATES[name]) {
    const [lat, lon] = PROVINCE_COORDINATES[name];
    return { lat, lon };
  }
  
  // 2. Try GeoJSON lookup (O(1))
  const lower = name.toLowerCase();
  if (PROVINCE_GEO_LOOKUP[lower]) return PROVINCE_GEO_LOOKUP[lower];
  
  // 3. Fallback: partial match scan (only if direct lookup fails)
  // This is rare so O(N) is acceptable here
  const key = Object.keys(PROVINCE_GEO_LOOKUP).find(k => k.includes(lower) || lower.includes(k));
  if (key) return PROVINCE_GEO_LOOKUP[key];

  return null;
};

const LEGEND_ITEMS = [
    { key: "all", color: THEME_COLORS.brand, label: "Tất cả" },
    { key: "storm", color: THEME_COLORS.storm, label: DISASTER_METADATA.storm.label },
    { key: "flood_landslide", color: THEME_COLORS.flash_flood, label: "Lũ / Sạt lở / Sụt lún" },
    { key: "heat_drought", color: THEME_COLORS.drought, label: "Nắng nóng / Hạn / Mặn" },
    { key: "wind_fog", color: THEME_COLORS.cold_surge, label: "Rét / Sương muối" },
    { key: "storm_surge", color: THEME_COLORS.storm_surge, label: DISASTER_METADATA.storm_surge.label },
    { key: "extreme_other", color: THEME_COLORS.extreme_weather, label: "Cực đoan khác" },
    { key: "wildfire", color: THEME_COLORS.wildfire, label: DISASTER_METADATA.wildfire.label },
    { key: "erosion", color: THEME_COLORS.erosion, label: DISASTER_METADATA.erosion.label },
    { key: "quake_tsunami", color: THEME_COLORS.earthquake, label: "Động đất / Sóng thần" },
    { key: "warning_forecast", color: THEME_COLORS.warning_forecast, label: DISASTER_METADATA.warning_forecast.label },
    { key: "recovery", color: THEME_COLORS.recovery, label: DISASTER_METADATA.recovery.label },
    { key: "community", color: THEME_COLORS.community, label: DISASTER_METADATA.community.label },
];

const MAPPING = {
    storm: ['storm'],
    flood_landslide: ['flood', 'flash_flood', 'landslide', 'subsidence'],
    heat_drought: ['heatwave', 'drought', 'salinity'],
    wind_fog: ['cold_surge'], 
    storm_surge: ['storm_surge'],
    extreme_other: ['extreme_weather', 'unknown'],
    wildfire: ['wildfire'],
    erosion: ['erosion'],
    quake_tsunami: ['earthquake', 'tsunami'],
    warning_forecast: ['warning_forecast'],
    recovery: ['recovery']
};

export default function MapPage() {
  const [dataEvents, setDataEvents] = useState([]); // Raw data from API
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Filters
  const [startDate, setStartDate] = useState(() => {
    return searchParams.get("start_date") || new Date().toISOString().split('T')[0];
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
            
            const [evs, crowd] = await Promise.all([
                getJson(query, { signal: controller.signal }),
                getJson("/api/user/crowdsource/approved", { signal: controller.signal })
            ]);
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

            // Process Crowd Reports: add a special type "community"
            const communityPoints = (crowd || []).map(r => ({
                id: `c_${r.id}`,
                title: `[Cộng đồng] ${r.description.substring(0, 50)}${r.description.length > 50 ? '...' : ''}`,
                lat: r.lat,
                lon: r.lon,
                disaster_type: 'community',
                started_at: r.created_at,
                source: 'Cộng đồng',
                is_community: true
            }));

            // Keep valid ones
            const allPoints = [
                ...enrichedEvents.filter(e => e.lat != null && e.lon != null),
                ...communityPoints.filter(p => p.lat != null && p.lon != null)
            ];
            setDataEvents(allPoints);
            
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
            setError(`Không thể tải dữ liệu bản đồ: ${e.message}`);
        } finally {
            setLoading(false);
        }
    })();

    return () => controller.abort();
  }, [startDate, endDate, activeFilter]);

  // Handle URL changes (Back button)
  useEffect(() => {
    const urlType = searchParams.get("type") || "all";
    const urlStart = searchParams.get("start_date") || new Date().toISOString().split('T')[0];
    const urlEnd = searchParams.get("end_date") || "";

    if (urlType !== activeFilter) setActiveFilter(urlType);
    if (urlStart !== startDate) setStartDate(urlStart);
    if (urlEnd !== endDate) setEndDate(urlEnd);
  }, [searchParams]);

  // Derived state for display
  const displayedEvents = useMemo(() => {
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
                     
                     <div className="flex items-center gap-2">
                        <DateFilter 
                            dateTime={startDate}
                            onChange={setStartDate}
                            placeholder="Từ ngày"
                            className="w-[120px]"
                        />
                        <span className="text-slate-400 font-bold">→</span>
                        <DateFilter 
                            dateTime={endDate}
                            onChange={setEndDate}
                            placeholder="Đến ngày"
                            className="w-[120px]"
                        />
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
