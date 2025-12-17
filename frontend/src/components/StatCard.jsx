import { ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function StatCard({ title, value, sub, icon: Icon, trend }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 tracking-tight">{value}</p>
        </div>
        {Icon && (
          <div className="rounded-xl bg-slate-100 p-2 text-slate-600 transition-colors group-hover:bg-blue-50 group-hover:text-blue-600">
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
      {sub && (
        <div className="mt-4 flex items-center text-xs text-slate-500">
          {trend === "up" && <ArrowUpRight className="mr-1 h-3 w-3 text-emerald-500" />}
          {trend === "down" && <ArrowDownRight className="mr-1 h-3 w-3 text-red-500" />}
          {sub}
        </div>
      )}
    </div>
  );
}
