import { Loader2 } from 'lucide-react';

/**
 * Standardized async button with loading state
 * 
 * @param {boolean} isLoading - Loading state
 * @param {string} loadingText - Text to show when loading
 * @param {React.ReactNode} children - Button text
 * @param {Component} icon - Lucide icon component
 * @param {string} variant - Button variant (primary|danger|success|secondary)
 * @param {string} className - Additional CSS classes
 */
export default function AsyncButton({ 
  isLoading, 
  loadingText, 
  children,
  icon: Icon,
  variant = "primary",
  className = "",
  disabled = false,
  ...props 
}) {
  const baseClass = "flex items-center gap-2 px-4 py-2 font-bold rounded-lg transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variantClasses = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    danger: "bg-red-600 text-white hover:bg-red-700",
    success: "bg-green-600 text-white hover:bg-green-700",
    secondary: "bg-slate-600 text-white hover:bg-slate-700",
    emerald: "bg-emerald-600 text-white hover:bg-emerald-700",
    indigo: "bg-indigo-600 text-white hover:bg-indigo-700"
  };
  
  return (
    <button 
      disabled={isLoading || disabled}
      className={`${baseClass} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>{loadingText || "Đang xử lý..."}</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4" />}
          <span>{children}</span>
        </>
      )}
    </button>
  );
}
