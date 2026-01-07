import React from "react";

const NationalHotlineCard = ({ item, style, isAdmin, onEdit, onDelete }) => {
  const CardIcon = style.icon;
  
  return (
    <div 
      style={{ borderColor: `${style.color}20` }}
      className="bg-white border-2 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all group relative h-full"
    >
      {isAdmin && (
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            onClick={() => onEdit(item)} 
            className="p-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
          <button 
            onClick={() => onDelete(item.id)} 
            className="p-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      )}
      <div 
        style={{ backgroundColor: `${style.color}10` }}
        className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
      >
        <CardIcon style={{ color: style.color }} className="w-6 h-6" />
      </div>
      <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{style.label}</div>
      <div style={{ color: style.color }} className="text-3xl font-black my-1">{item.phone}</div>
      <div className="text-xs font-semibold text-slate-600 leading-tight">{item.agency}</div>
    </div>
  );
};

export default NationalHotlineCard;
