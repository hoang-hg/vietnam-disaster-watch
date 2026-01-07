import React from "react";
import { MapPin, Phone, Edit2, Trash2 } from "lucide-react";

const HotlineGridItem = ({ item: h, isAdmin, onEdit, onDelete }) => {
  return (
    <div className="p-4 hover:bg-slate-50 transition-colors flex justify-between items-start group/item relative">
      <div className="flex-1 min-w-0 pr-4">
        <div className="font-bold text-slate-900 text-sm truncate">{h.province}</div>
        <div className="text-[10px] text-slate-400 uppercase font-black truncate">{h.agency}</div>
        {h.address && (
          <div className="mt-1 text-xs text-slate-500 line-clamp-2">
            <MapPin className="w-3 h-3 inline mr-1 text-slate-400" />
            {h.address}
          </div>
        )}
      </div>
      <div className="flex flex-col items-end gap-2">
        <div className="flex items-center gap-2 text-blue-600 font-black text-sm">
          {h.phone}
          <Phone className="w-3.5 h-3.5" />
        </div>
        {isAdmin && (
          <div className="flex gap-1 pt-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
            <button 
                onClick={() => onEdit(h)} 
                className="p-1.5 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200"
            >
              <Edit2 className="w-3 h-3" />
            </button>
            <button 
                onClick={() => onDelete(h.id)} 
                className="p-1.5 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default HotlineGridItem;
