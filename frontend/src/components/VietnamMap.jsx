import { MapContainer, TileLayer, Marker, Popup, useMapEvents, useMap } from 'react-leaflet';
import React, { useEffect } from 'react';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { THEME_COLORS } from '../theme';
import { fmtType } from '../api';
import { Link } from 'react-router-dom';

// Fix for default marker icon issues in React Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: null,
  iconUrl: null,
  shadowUrl: null,
});

// Memoize icons to prevent recreation on every render
const iconCache = {};

// Enhanced Logic to get icon
function getIcon(type, isCritical = false) {
  // 1. Get Base Color from unified theme
  let color = THEME_COLORS[type] || THEME_COLORS.unknown;
  
  // Specific override for Community to ensure visibility
  if (type === 'community') color = THEME_COLORS.community;

  // 2. Generate Unique Cache Key
  const key = `${type}-${isCritical ? 'crit' : 'std'}`;

  // 3. Create or Return Cached Icon
  if (!iconCache[key]) {
    // Pulse animation for critical events (Storm, Landslide, Flash Flood)
    const pulseEffect = isCritical 
      ? `<span class="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping" style="background-color: ${color}"></span>` 
      : `<span class="absolute inline-flex h-full w-full rounded-full opacity-20" style="background-color: ${color}"></span>`;
      
    iconCache[key] = L.divIcon({
      className: "bg-transparent",
      html: `
        <div class="relative flex items-center justify-center w-8 h-8 group hover:scale-110 transition-transform ${isCritical ? 'z-50' : ''}">
            ${pulseEffect}
            <span class="relative inline-flex items-center justify-center w-4 h-4 rounded-full border border-white shadow-md z-10" style="background-color: ${color}"></span>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      popupAnchor: [0, -10]
    });
  }
  return iconCache[key];
}

function MapEvents({ onBoundsChange }) {
  const map = useMap();
  
  // Set initial bounds
  useEffect(() => {
    const bounds = map.getBounds();
    onBoundsChange({
      minLat: bounds.getSouth(),
      maxLat: bounds.getNorth(),
      minLon: bounds.getWest(),
      maxLon: bounds.getEast(),
    });
  }, []);

  useMapEvents({
    moveend: () => {
      const bounds = map.getBounds();
      onBoundsChange({
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLon: bounds.getWest(),
        maxLon: bounds.getEast(),
      });
    },
    zoomend: () => {
      const bounds = map.getBounds();
      onBoundsChange({
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLon: bounds.getWest(),
        maxLon: bounds.getEast(),
      });
    },
  });
  return null;
}

const VietnamMap = ({ points, onBoundsChange }) => {
  const center = [16.5, 107.0]; 

  return (
    <MapContainer 
        center={center} 
        zoom={5} 
        scrollWheelZoom={true} 
        zoomControl={true} 
        attributionControl={false}
        className="w-full h-full z-0 font-sans"
        style={{ background: '#aadaff' }}
    >
      {onBoundsChange && <MapEvents onBoundsChange={onBoundsChange} />}
      <TileLayer
        attribution='&copy; Google Maps'
        url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}&hl=vi&gl=vn"
      />

      <MarkerClusterGroup chunkedLoading maxClusterRadius={40} spiderfyOnMaxZoom={true}>
      {points.map((p) => {
        if (typeof p.lat !== 'number' || typeof (p.lon ?? p.lng) !== 'number') return null;
        
        const type = p.disaster_type || p.type;
        // Determine Criticality for Pulse Effect
        const isCritical = ['storm', 'landslide', 'flash_flood'].includes(type) || (p.deaths > 0);
        const icon = getIcon(type, isCritical);

        return (
          <Marker key={p.id} position={[p.lat, p.lon ?? p.lng]} icon={icon}>
            <Popup>
              <div className="min-w-[220px] font-sans p-3">
                <Link 
                  to={`/events/${p.id}`} 
                  className="font-bold text-slate-800 dark:text-white text-sm mb-2 leading-tight block hover:text-[#2fa1b3] transition-colors"
                >
                  {p.title}
                </Link>
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-200/50 dark:border-slate-700/50">
                    <span 
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider text-white shadow-sm"
                        style={{ backgroundColor: THEME_COLORS[p.disaster_type || p.type] || THEME_COLORS.unknown }}
                    >
                        {fmtType(p.disaster_type || p.type)}
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 font-bold">
                        {new Date(p.started_at || p.published_at).toLocaleDateString("vi-VN")}
                    </span>
                </div>
              </div>
            </Popup>
          </Marker>
        );
      })}
      </MarkerClusterGroup>
    </MapContainer>
  );
};

export default React.memo(VietnamMap);
