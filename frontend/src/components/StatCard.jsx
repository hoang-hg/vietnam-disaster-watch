import { ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function StatCard({ title, value, sub, icon: Icon, trend, color = "text-blue-600", onClick, active }) {
  // Extract base color (e.g., from 'text-red-500' get 'red')
  const colorMatch = color.match(/text-([a-z]+)-/);
  const baseColor = colorMatch ? colorMatch[1] : "blue";
  
  const COLOR_MAPS = {
    blue: {
      border: "border-blue-500",
      ring: "ring-blue-500/20",
      iconBg: "bg-blue-50",
      iconText: "text-blue-600",
      iconActive: "bg-blue-600 text-white",
      hover: "hover:border-blue-300"
    },
    indigo: {
      border: "border-indigo-500",
      ring: "ring-indigo-500/20",
      iconBg: "bg-indigo-50",
      iconText: "text-indigo-600",
      iconActive: "bg-indigo-600 text-white",
      hover: "hover:border-indigo-300"
    },
    red: {
      border: "border-red-500",
      ring: "ring-red-500/20",
      iconBg: "bg-red-50",
      iconText: "text-red-600",
      iconActive: "bg-red-600 text-white",
      hover: "hover:border-red-300"
    },
    emerald: {
      border: "border-emerald-500",
      ring: "ring-emerald-500/20",
      iconBg: "bg-emerald-50",
      iconText: "text-emerald-600",
      iconActive: "bg-emerald-600 text-white",
      hover: "hover:border-emerald-300"
    },
    slate: {
      border: "border-slate-500",
      ring: "ring-slate-500/20",
      iconBg: "bg-slate-50",
      iconText: "text-slate-600",
      iconActive: "bg-slate-600 text-white",
      hover: "hover:border-slate-300"
    }
  };

  const scheme = COLOR_MAPS[baseColor] || COLOR_MAPS.blue;

  return (
    <div 
      onClick={onClick}
      className={`group relative overflow-hidden rounded-2xl border transition-all duration-300 cursor-pointer ${
        active 
          ? `${scheme.border} ring-4 ${scheme.ring} shadow-lg bg-white dark:bg-slate-900` 
          : `border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 ${scheme.hover} dark:hover:border-slate-600 hover:shadow-md hover:-translate-y-1`
      } p-5`}
    >
      <div className="flex justify-between items-start">
        <div className="max-w-[70%]">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 line-clamp-1">{title}</p>
          <p className={`mt-2 ${typeof value === 'string' && value.length > 10 ? 'text-xl' : 'text-3xl'} font-bold text-slate-900 dark:text-white tracking-tight line-clamp-1`}>
            {value}
          </p>
        </div>
        {Icon && (
          <div className={`rounded-xl p-2 transition-all duration-500 ${active ? scheme.iconActive : `${scheme.iconBg} dark:bg-slate-800 ${scheme.iconText} group-hover:bg-opacity-80 group-hover:rotate-12 group-hover:scale-110`}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
      {sub && (
        <div className="mt-4 flex items-center text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap overflow-hidden">
          {trend === "up" && <ArrowUpRight className="mr-1 h-3 w-3 text-emerald-500" />}
          {trend === "down" && <ArrowDownRight className="mr-1 h-3 w-3 text-red-500" />}
          <span className="truncate">{sub}</span>
        </div>
      )}
    </div>
  );
}
