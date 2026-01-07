import React from "react";
import { fmtVndBillion } from "../../api.js";

const ImpactBreakdown = ({ details }) => {
  if (!details || Object.keys(details).length === 0) return null;

  return (
    <div className="mt-8 space-y-4">
      <div className="flex items-center gap-2 text-slate-800 font-bold">
        <span className="w-1.5 h-5 bg-red-500 rounded-full"></span>
        Chi tiết thiệt hại trích xuất
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Housing Details */}
        {details.homes?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
              Nhà cửa & Công trình
            </div>
            <div className="space-y-2">
              {details.homes.map((h, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="text-slate-600 truncate mr-2">{h.status || 'Hư hại'}</span>
                  <span className="font-bold text-slate-900 whitespace-nowrap">{h.num} {h.unit || 'căn'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agriculture Details */}
        {details.agriculture?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              Nông nghiệp & Chăn nuôi
            </div>
            <div className="space-y-2">
              {details.agriculture.map((a, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="text-slate-600 truncate mr-2">{a.crop || a.livestock || 'Diện tích'} {a.status ? `(${a.status})` : ''}</span>
                  <span className="font-bold text-slate-900 whitespace-nowrap">{a.num} {a.unit}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Disruption Details */}
        {details.disruption?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-slate-500"></div>
              Giao thông & Đời sống
            </div>
            <div className="space-y-2">
              {details.disruption.map((d, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="text-slate-600 truncate mr-2">{d.obj || 'Số lượng'}</span>
                  <span className="font-bold text-slate-900 whitespace-nowrap">{d.num || ''} {d.unit || 'lần'}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImpactBreakdown;
