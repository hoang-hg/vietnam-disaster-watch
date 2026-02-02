import React from "react";
import { Link } from "react-router-dom";
import { 
  MapPin, Clock, FileText, Zap, Users, Activity, DollarSign, Filter, Trash2
} from "lucide-react";
import { 
  getDisasterMeta, fmtType, isJunkImage, fmtTimeAgo, fmtVndBillion, cleanText, toUtcDate 
} from "../../api.js";
import Badge from "../Badge.jsx";
import logoIge from "../../assets/logo_ige.png";

const DamageBadges = ({ e }) => {
  const prioritized = [];
  const details = e.details || {};
  
  if (e.deaths > 0) prioritized.push({ type: 'deaths', label: `${e.deaths} chết`, priority: 100, color: 'red', icon: Zap });
  if (e.missing > 0) prioritized.push({ type: 'missing', label: `${e.missing} mất tích`, priority: 90, color: 'orange', icon: Users });
  if (e.injured > 0) prioritized.push({ type: 'injured', label: `${e.injured} bị thương`, priority: 80, color: 'yellow', icon: Activity });
  if (e.damage_billion_vnd > 0) prioritized.push({ type: 'damage', label: fmtVndBillion(e.damage_billion_vnd), priority: 70, color: 'blue', icon: DollarSign });
  
  if (details.homes && details.homes.length > 0) {
    const best = details.homes.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.homes[0]);
    prioritized.push({ type: 'homes', label: `${best.num} ${best.unit || 'nhà'}`, priority: 60, color: 'indigo', icon: MapPin });
  }
  if (details.disruption && details.disruption.length > 0) {
    const best = details.disruption.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.disruption[0]);
    prioritized.push({ type: 'disruption', label: `${best.num} ${best.unit || 'di dời'}`, priority: 55, color: 'slate', icon: Users });
  }
  if (details.agriculture && details.agriculture.length > 0) {
    const best = details.agriculture.reduce((prev, curr) => (curr.num > prev.num ? curr : prev), details.agriculture[0]);
    prioritized.push({ type: 'agriculture', label: `${best.num} ${best.unit || 'ha'}`, priority: 50, color: 'green', icon: Filter });
  }
  
  prioritized.sort((a, b) => b.priority - a.priority);
  
  return (
    <div className="flex flex-wrap gap-2 mb-4 min-h-[32px]">
      {prioritized.slice(0, 2).map((item) => {
        const Icon = item.icon;
        const colorClass = { 
          red: "text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30",
          orange: "text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 border border-orange-100 dark:border-orange-900/30",
          yellow: "text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-100 dark:border-yellow-900/30",
          blue: "text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900/30", 
          indigo: "text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-900/30", 
          slate: "text-slate-700 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700",
          green: "text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-900/30"
        }[item.color] || "text-slate-700 dark:text-slate-400 bg-slate-50 dark:bg-slate-800";
        
        return (
          <div key={item.type} className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1.5 rounded-lg shadow-sm ${colorClass}`}>
            <Icon className="w-3.5 h-3.5" />
            <span>{item.label}</span>
          </div>
        );
      })}
    </div>
  );
};

const EventCard = React.memo(({ event: e, isAdmin, onDelete }) => {
  const meta = getDisasterMeta(e.disaster_type);
  
  return (
    <Link
      to={`/events/${e.id}`}
      className={`block group bg-white dark:bg-slate-900 rounded-2xl border-2 dark:border-slate-800 hover:shadow-2xl hover:-translate-y-1 transition-all duration-500 flex flex-col overflow-hidden relative shadow-sm ${e.disaster_type === 'warning_forecast' ? 'border-dashed' : 'border-solid'}`}
      style={{ borderColor: meta.color }}
    >
      <div className="h-1 w-full" style={{ backgroundColor: meta.color }}></div>
      <div className="w-full h-44 overflow-hidden relative flex items-center justify-center bg-slate-100/30">
        {e.image_url && !isJunkImage(e.image_url) ? (
          <img 
            src={e.image_url} 
            alt={e.title} 
            loading="lazy"
            className={
              e.image_url.endsWith('.svg')
                ? "w-24 h-24 object-contain opacity-50 dark:opacity-80 transition-transform duration-500 group-hover:scale-110" 
                : "w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000"
            }
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center p-4 bg-white dark:bg-slate-800 relative overflow-hidden">
            <div className="absolute inset-0 opacity-5" style={{ backgroundColor: meta.color }}></div>
            <img 
              src={logoIge} 
              alt="Logo IGE" 
              className="w-36 h-36 object-contain opacity-90 dark:opacity-20 group-hover:scale-110 transition-transform duration-700 grayscale group-hover:grayscale-0 dark:invert" 
            />
            <div className="mt-2 h-1 w-16 rounded-full opacity-50" style={{ backgroundColor: meta.color }}></div>
          </div>
        )}
        <div className="absolute top-4 left-4 flex flex-col items-start gap-2">
          <Badge tone={meta.tone} className="shadow-md">
            {fmtType(e.disaster_type)}
          </Badge>
          {e.needs_verification === 1 && (e.deaths > 0 || e.missing > 0 || e.damage_billion_vnd >= 1) && (
            <div className="bg-red-600 text-white text-[9px] font-black uppercase px-2 py-0.5 rounded-full shadow-lg border border-red-400/30">
              Cần kiểm chứng
            </div>
          )}
        </div>
        
        {isAdmin && (
          <div className="absolute top-3 right-3 flex items-center gap-1 z-30">
            <button 
              onClick={(evt) => {
                evt.preventDefault();
                evt.stopPropagation();
                onDelete(e.id);
              }}
              className="group/del flex items-center gap-1.5 px-3 py-1.5 bg-white/95 backdrop-blur-sm hover:bg-red-600 text-red-600 hover:text-white rounded-xl shadow-lg border border-red-100 transition-all duration-300 transform"
              title="Xóa sự kiện"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="text-[10px] font-black uppercase tracking-tighter">Xóa</span>
            </button>
          </div>
        )}
      </div>

      <div className="p-5 flex-1 flex flex-col">
        <h2 className="text-[15px] font-bold text-slate-900 dark:text-white line-clamp-2 mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-snug h-11">
          {cleanText(e.title)}
        </h2>
        <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400 mb-5">
          {e.province && (
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
              <MapPin className="w-3 h-3 text-slate-400" />
              <span className="font-medium">{e.province}</span>
            </div>
          )}
          <div className="flex items-center gap-1 font-medium">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>{fmtTimeAgo(e.started_at)}</span>
          </div>
          {e.source && (
            <span className="font-bold text-red-500 dark:text-red-400 uppercase ml-auto">
              {(e.source || "").replace(/(\.com\.vn|\.vn|\.com|https?:\/\/|www\.)/g, '').toUpperCase()}
            </span>
          )}
        </div>

        <DamageBadges e={e} />

        <div className="mt-auto pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
          <div className="flex items-center gap-1">
            <FileText className="w-3 h-3" />
            <span>{e.sources_count || 1} nguồn tin</span>
          </div>
          <span>{toUtcDate(e.started_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})}</span>
        </div>
      </div>
    </Link>
  );
});

export default EventCard;
