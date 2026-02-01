import React from "react";

const NationalHotlineCard = ({ item, style, isAdmin, onEdit, onDelete }) => {
  const CardIcon = style.icon;
  
  return (
    <div 
      style={{ borderColor: `${style.color}40` }}
      className="bg-white dark:bg-slate-900 border-2 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all group relative h-full flex flex-col items-center text-center"
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
        style={{ backgroundColor: `${style.color}15` }}
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm"
      >
        <CardIcon style={{ color: style.color }} className="w-7 h-7" />
      </div>
      
      {/* Editable Label (Agency) */}
      <div className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">
        {item.agency ? item.agency : style.label}
      </div>
      
      {/* Phone Number */}
      <div style={{ color: style.color }} className="text-4xl font-black mb-2 tracking-tight">
        {item.phone}
      </div>
      
      {/* Editable Description (Address) or Default */}
      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 leading-tight px-4 opacity-80">
        {item.address ? item.address : style.description}
      </div>
    </div>
  );
};

export default NationalHotlineCard;
