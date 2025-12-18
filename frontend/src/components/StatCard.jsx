import { ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function StatCard({ title, value, sub, icon: Icon, trend, color = "text-blue-600" }) {
  // Extract base color (e.g., from 'text-red-500' get 'red')
  const colorMatch = color.match(/text-([a-z]+)-/);
  const baseColor = colorMatch ? colorMatch[1] : "blue";
  
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
      <div className="flex justify-between items-start">
        <div className="max-w-[70%]">
          <p className="text-sm font-medium text-slate-500 line-clamp-1">{title}</p>
          <p className={`mt-2 ${typeof value === 'string' && value.length > 10 ? 'text-xl' : 'text-3xl'} font-bold text-slate-900 tracking-tight line-clamp-1`}>
            {value}
          </p>
        </div>
        {Icon && (
          <div className={`rounded-xl p-2 transition-colors bg-${baseColor}-50 text-${baseColor}-600 group-hover:bg-${baseColor}-100`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
      {sub && (
        <div className="mt-4 flex items-center text-xs text-slate-500 whitespace-nowrap overflow-hidden">
          {trend === "up" && <ArrowUpRight className="mr-1 h-3 w-3 text-emerald-500" />}
          {trend === "down" && <ArrowDownRight className="mr-1 h-3 w-3 text-red-500" />}
          <span className="truncate">{sub}</span>
        </div>
      )}
    </div>
  );
}
