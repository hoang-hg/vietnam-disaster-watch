import React from "react";
import { Search, Plus, MapPin, X } from "lucide-react";

const HotlineFilterBar = ({ 
  filterProvince, 
  setFilterProvince, 
  searchTerm, 
  setSearchTerm, 
  isAdmin, 
  onAdd, 
  allProvinces, 
  totalCount 
}) => {
  return (
    <div className="p-6 border-b border-slate-100 flex flex-col lg:flex-row justify-between items-center gap-4">
      <h3 className="font-black text-slate-900 flex items-center gap-2 uppercase tracking-tight text-sm">
        <MapPin className="w-4 h-4 text-blue-600" /> 
        {filterProvince !== "Toàn quốc" ? `Đường dây nóng ${filterProvince}` : "Đường dây nóng các tỉnh thành"}
        <span className="ml-1 text-slate-400 font-medium normal-case">({totalCount} liên hệ)</span>
      </h3>
      
      <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto items-center">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select 
            value={filterProvince}
            onChange={(e) => setFilterProvince(e.target.value)}
            className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-full sm:w-auto cursor-pointer"
          >
            {allProvinces.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          
          {filterProvince !== "Toàn quốc" && (
            <button 
              onClick={() => setFilterProvince("Toàn quốc")}
              className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-500 rounded-xl transition-colors"
              title="Xem tất cả"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        <div className="relative w-full sm:w-64">
           <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
           <input 
              type="text" 
              placeholder="Tìm theo tên, số điện thoại..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
           />
        </div>

        {isAdmin && (
          <button 
            onClick={onAdd}
            className="px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-green-700 transition-colors shadow-sm whitespace-nowrap"
          >
            <Plus className="w-4 h-4" /> Thêm mới
          </button>
        )}
      </div>
    </div>
  );
};

export default HotlineFilterBar;
