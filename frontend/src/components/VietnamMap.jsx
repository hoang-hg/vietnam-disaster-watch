import { MapContainer, TileLayer, Marker, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { THEME_COLORS } from '../theme';
import { fmtType } from '../api';
import VIETNAM_LOCATIONS from '../data/vietnam_locations.json';

// Fix for default marker icon issues in React Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: null,
  iconUrl: null,
  shadowUrl: null,
});

export default function VietnamMap({ points }) {
  const center = [16.0, 108.0];

  return (
    <MapContainer 
        center={center} 
        zoom={5} 
        scrollWheelZoom={true} // Enable scroll
        zoomControl={true} // Enable button
        className="w-full h-full z-0"
        style={{ background: '#f8fafc' }}
    >
      <TileLayer
        attribution='&copy; Google Maps'
        url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
      />



      {/* Dynamic Disaster Events */}
      {points.map((p) => {
        // Use real lat/lon if available, fallback to nothing
        if (typeof p.lat !== 'number' || typeof p.lon !== 'number') return null;
        
        // Color based on type
        const color = THEME_COLORS[p.disaster_type] || THEME_COLORS.unknown;
        // Tailwind mapped color for the ripple usually needs to be hex, THEME_COLORS has names. 
        // For simplicity let's stick to a safe default map or expand THEME_COLORS logic.
        // Actually THEME_COLORS in theme.js might be distinct names (blue, red) not hex.
        // Let's use a mapping for safety or hex values.
        
        // Custom ripple effect marker
        
        // Render icon
        const icon = L.divIcon({
          className: "bg-transparent",
          html: `
            <div class="relative flex items-center justify-center w-8 h-8 group hover:scale-110 transition-transform">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style="background-color: ${color}"></span>
                <span class="relative inline-flex items-center justify-center w-6 h-6 rounded-full border-2 border-white shadow-md text-white font-bold" style="background-color: ${color}">
                    
                </span>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });

        return (
          <Marker key={p.id} position={[p.lat, p.lon]} icon={icon}>
            <Popup>
              <div className="min-w-[200px]">
                <div className="font-semibold text-slate-800 text-sm mb-1 leading-tight">{p.title}</div>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                    <span 
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide text-white"
                        style={{ backgroundColor: THEME_COLORS[p.disaster_type] || THEME_COLORS.unknown }}
                    >
                        {fmtType(p.disaster_type)}
                    </span>
                    {p.risk_level && (
                        <span className="text-xs font-medium text-slate-500">Rủi ro cấp {p.risk_level}</span>
                    )}
                </div>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
