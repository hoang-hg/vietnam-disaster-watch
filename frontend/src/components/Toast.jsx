import React, { useEffect } from 'react';
import { CheckCircle, XCircle, X, Info, AlertTriangle } from 'lucide-react';

export default function Toast({ 
  message, 
  type = 'success', 
  isVisible, 
  onClose, 
  duration = 3000 
}) {
  useEffect(() => {
    if (isVisible && duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [isVisible, duration, onClose]);

  if (!isVisible) return null;

  const styles = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800 shadow-emerald-100',
    error: 'bg-red-50 border-red-200 text-red-800 shadow-red-100',
    warning: 'bg-amber-50 border-amber-200 text-amber-800 shadow-amber-100',
    info: 'bg-blue-50 border-blue-200 text-blue-800 shadow-blue-100'
  }[type];

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-emerald-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />
  }[type];

  return (
    <div className="fixed top-6 right-6 z-[300] animate-in slide-in-from-right-full duration-300 no-print">
      <div className={`flex items-center gap-3 px-4 py-3 rounded-2xl border shadow-xl ${styles} min-w-[300px]`}>
        <div className="shrink-0">
          {icons}
        </div>
        <div className="flex-1 text-sm font-bold leading-tight">
          {message}
        </div>
        <button 
          onClick={onClose}
          className="p-1 hover:bg-black/5 rounded-lg transition-colors text-current/50"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
