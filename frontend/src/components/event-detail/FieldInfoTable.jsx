import React from "react";

const FieldInfoTable = ({ isEditing, ev, editForm, setEditForm }) => {
  const hasContent = ev.commune || ev.village || ev.route || ev.cause || ev.characteristics;
  if (!isEditing && !hasContent) return null;

  return (
    <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
        <div className="w-1.5 h-4 bg-blue-600 rounded-full"></div>
        <span className="text-sm font-bold text-slate-800 uppercase tracking-tight">Thông tin thực địa (Trích xuất)</span>
      </div>
      <table className="min-w-full divide-y divide-slate-100">
        <tbody className="divide-y divide-slate-50 text-sm">
          {(isEditing || ev.commune) && (
            <tr>
              <td className="px-4 py-3 font-medium text-slate-500 w-1/3 bg-slate-50/50 text-xs uppercase tracking-wider">Xã/Phường</td>
              <td className="px-4 py-3 text-slate-900 font-semibold">
                {isEditing ? (
                  <input 
                    value={editForm.commune || ""} 
                    onChange={e => setEditForm({...editForm, commune: e.target.value})} 
                    className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                ) : ev.commune}
              </td>
            </tr>
          )}
          {(isEditing || ev.village) && (
            <tr>
              <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Thôn/Bản/Xóm</td>
              <td className="px-4 py-3 text-slate-900">
                {isEditing ? (
                  <input 
                    value={editForm.village || ""} 
                    onChange={e => setEditForm({...editForm, village: e.target.value})} 
                    className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                ) : ev.village}
              </td>
            </tr>
          )}
          {(isEditing || ev.route) && (
            <tr>
              <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Tuyến đường</td>
              <td className="px-4 py-3 text-slate-900 font-mono text-xs">
                {isEditing ? (
                  <input 
                    value={editForm.route || ""} 
                    onChange={e => setEditForm({...editForm, route: e.target.value})} 
                    className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                ) : ev.route}
              </td>
            </tr>
          )}
          {(isEditing || ev.cause) && (
            <tr>
              <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Nguyên nhân</td>
              <td className="px-4 py-3">
                {isEditing ? (
                  <input 
                    value={editForm.cause || ""} 
                    onChange={e => setEditForm({...editForm, cause: e.target.value})} 
                    className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                ) : (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${ev.cause?.includes('Mưa') ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                    {ev.cause}
                  </span>
                )}
              </td>
            </tr>
          )}
          {(isEditing || ev.characteristics) && (
            <tr>
              <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Đặc điểm / Quy mô</td>
              <td className="px-4 py-3 text-slate-800 leading-relaxed italic">
                {isEditing ? (
                  <textarea 
                    value={editForm.characteristics || ""} 
                    onChange={e => setEditForm({...editForm, characteristics: e.target.value})} 
                    className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none" 
                    rows={3} 
                  />
                ) : `"${ev.characteristics}"`}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default FieldInfoTable;
