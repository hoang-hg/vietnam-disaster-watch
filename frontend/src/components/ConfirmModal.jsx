import React from 'react';
import { X, AlertTriangle, Trash2, CheckCircle } from 'lucide-react';

export default function ConfirmModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = "Xác nhận xóa", 
  message = "Bạn có chắc chắn muốn thực hiện hành động này?",
  confirmLabel = "Xóa ngay",
  cancelLabel = "Hủy bỏ",
  variant = "danger" // 'danger', 'warning', 'success'
}) {
  if (!isOpen) return null;

  const getIcon = () => {
    switch(variant) {
      case 'success': return <CheckCircle className="w-6 h-6" />;
      case 'warning': return <AlertTriangle className="w-6 h-6" />;
      default: return <Trash2 className="w-6 h-6" />;
    }
  };

  const getIconBg = () => {
    switch(variant) {
      case 'success': return 'bg-emerald-50 text-emerald-600';
      case 'warning': return 'bg-amber-50 text-amber-600';
      default: return 'bg-red-50 text-red-600';
    }
  };

  const getButtonClass = () => {
    switch(variant) {
      case 'success': return 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200';
      case 'warning': return 'bg-amber-600 hover:bg-amber-700 shadow-amber-200';
      case 'info': return 'bg-blue-600 hover:bg-blue-700 shadow-blue-200';
      default: return 'bg-red-600 hover:bg-red-700 shadow-red-200';
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-[200] p-4 no-print animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-3xl w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden border border-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <div className={`p-3 rounded-2xl ${getIconBg()}`}>
              {getIcon()}
            </div>
            <button 
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <h3 className="text-xl font-black text-slate-900 mb-2 leading-tight">
            {title}
          </h3>
          <p className="text-slate-500 text-sm leading-relaxed">
            {message}
          </p>
        </div>

        <div className="p-6 bg-slate-50/50 border-t border-slate-100 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 rounded-xl bg-white border border-slate-200 text-slate-700 text-sm font-bold hover:bg-slate-50 transition-all active:scale-95"
          >
            {cancelLabel}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`flex-1 px-4 py-3 rounded-xl text-white text-sm font-bold shadow-lg transition-all active:scale-95 ${getButtonClass()}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
