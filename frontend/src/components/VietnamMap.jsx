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
        scrollWheelZoom={false} 
        className="w-full h-full z-0"
        style={{ background: '#f8fafc' }}
    >
      <TileLayer
        attribution='&copy; Google Maps'
        url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
      />



      {/* Dynamic Disaster Events */}
      {points.map((p) => {
        if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return null;
        
        // Use Red for all "risky" points as requested, or fall back to theme color if preferred.
        // The user request: "những tỉnh có điểm nóng rủi ro trong ngày bôi đỏ"
        // interpreting as: make the event marker red.
        const color = '#ef4444'; // Red-500
        
        // Custom ripple effect marker
        const icon = L.divIcon({
          className: "bg-transparent",
          html: `
            <div class="relative flex items-center justify-center w-6 h-6">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style="background-color: ${color}"></span>
                <span class="relative inline-flex w-3 h-3 rounded-full border border-white shadow-sm" style="background-color: ${color}"></span>
            </div>
          `,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });

        return (
          <Marker key={p.id} position={[p.lat, p.lng]} icon={icon}>
            <Popup>
              <div className="min-w-[200px]">
                <div className="font-semibold text-slate-800 text-sm mb-1 leading-tight">{p.title}</div>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                    <span 
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide text-white"
                        style={{ backgroundColor: THEME_COLORS[p.type] || THEME_COLORS.unknown }}
                    >
                        {fmtType(p.type)}
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
