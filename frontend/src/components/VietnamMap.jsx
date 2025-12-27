import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
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

export default function VietnamMap({ points }) {
  const center = [16.5, 107.0]; // Slightly adjusted center for "Big Vietnam" feel

  return (
    <MapContainer 
        center={center} 
        zoom={5} // Zoom 5 makes Vietnam fill the view (desktop)
        scrollWheelZoom={true} 
        zoomControl={true} 
        className="w-full h-full z-0 font-sans"
        style={{ background: '#aadaff' }}
    >
      <TileLayer
        attribution='&copy; Google Maps'
        url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}&hl=vi&gl=vn"
      />

      {/* Dynamic Disaster Events with Clustering */}
      <MarkerClusterGroup
        chunkedLoading
        maxClusterRadius={40}
        showCoverageOnHover={false}
        spiderfyOnMaxZoom={true}
      >
        {points.map((p) => {
          if (typeof p.lat !== 'number' || typeof (p.lon || p.lng) !== 'number') return null;
          
          const color = THEME_COLORS[p.disaster_type || p.type] || THEME_COLORS.unknown;
          
          const icon = L.divIcon({
            className: "bg-transparent",
            html: `
              <div class="relative flex items-center justify-center w-8 h-8 group hover:scale-110 transition-transform">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style="background-color: ${color}"></span>
                  <span class="relative inline-flex items-center justify-center w-4 h-4 rounded-full border border-white shadow-md" style="background-color: ${color}"></span>
              </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
          });

          return (
            <Marker key={p.id} position={[p.lat, p.lon || p.lng]} icon={icon}>
              <Popup>
                <div className="min-w-[200px] font-sans">
                  <Link 
                    to={`/events/${p.id}`} 
                    className="font-bold text-slate-800 text-sm mb-1 leading-tight block hover:text-teal-600 transition-colors"
                  >
                    {p.title}
                  </Link>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                      <span 
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide text-white"
                          style={{ backgroundColor: THEME_COLORS[p.disaster_type || p.type] || THEME_COLORS.unknown }}
                      >
                          {fmtType(p.disaster_type || p.type)}
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">
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
}
