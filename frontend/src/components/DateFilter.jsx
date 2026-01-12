import { useRef } from "react";
import { Calendar, X } from "lucide-react";
import PropTypes from "prop-types";

export default function DateFilter({ 
  dateTime, 
  onChange, 
  onClear,
  placeholder = "Tất cả thời gian",
  className = "",
  showClear = false
}) {
  const dateInputRef = useRef(null);

  const displayLabel = dateTime 
    ? dateTime.split('-').reverse().join('/') 
    : placeholder;

  const handleChange = (e) => {
    if (onChange) {
        onChange(e.target.value); 
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div 
        onClick={() => dateInputRef.current?.showPicker()}
        className="relative flex-1 flex items-center justify-between gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-1.5 shadow-sm group hover:border-[#2fa1b3] dark:hover:border-blue-500 transition-all cursor-pointer min-w-[140px]"
      >
        <span className={`text-sm font-bold whitespace-nowrap ${dateTime ? 'text-slate-900 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'}`}>
           {displayLabel}
        </span>
        <Calendar className="w-4 h-4 text-[#2fa1b3] group-hover:scale-110 transition-transform flex-shrink-0" />
        
        {/* Hidden Native Picker */}
        <input 
            ref={dateInputRef}
            type="date"
            value={dateTime || ""} 
            onChange={handleChange}
            className="absolute inset-0 opacity-0 -z-10 pointer-events-none"
        />
      </div>
      
      {/* External Clear Button */}
      {showClear && onClear && (
        <button 
           onClick={(e) => {
             e.stopPropagation();
             onClear();
           }}
           className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-slate-200 dark:border-slate-700 shadow-sm"
           title="Xóa bộ lọc"
        >
           <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

DateFilter.propTypes = {
  dateTime: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onClear: PropTypes.func,
  placeholder: PropTypes.string,
  className: PropTypes.string,
  showClear: PropTypes.bool
};
