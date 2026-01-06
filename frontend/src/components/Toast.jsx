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
    success: 'bg-white dark:bg-slate-900 border-2 border-emerald-500 text-emerald-800 dark:text-emerald-300',
    error: 'bg-white dark:bg-slate-900 border-2 border-red-500 text-red-800 dark:text-red-300',
    warning: 'bg-white dark:bg-slate-900 border-2 border-amber-500 text-amber-800 dark:text-amber-300',
    info: 'bg-white dark:bg-slate-900 border-2 border-blue-500 text-blue-800 dark:text-blue-300'
  }[type];

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-emerald-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />
  }[type];

  return (
    <div className="fixed top-6 right-6 z-[300] animate-in slide-in-from-right-full fade-in duration-500 no-print">
      <div className={`flex items-center gap-4 px-5 py-4 rounded-2xl shadow-2xl ${styles} min-w-[320px] relative overflow-hidden`}>
        <div className="shrink-0 scale-110">
          {icons}
        </div>
        <div className="flex-1 text-sm font-black uppercase tracking-tight leading-tight">
          {message}
        </div>
        <button 
          onClick={onClose}
          className="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl transition-colors text-current/40 hover:text-current"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Action Progress Bar */}
        <div className="absolute bottom-0 left-0 h-1 bg-current opacity-20 w-full animate-toast-progress origin-left" 
             style={{ animationDuration: `${duration}ms` }} />
      </div>
    </div>
  );
}
