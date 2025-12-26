import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Frontend Crash Detected:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex flex-col items-center justify-center p-8 text-center bg-red-50 rounded-2xl border-2 border-dashed border-red-200 m-4">
          <div className="bg-red-100 p-4 rounded-full mb-4">
            <AlertTriangle className="w-12 h-12 text-red-600" />
          </div>
          <h2 className="text-2xl font-black text-red-700 mb-2 uppercase tracking-tight">Hệ thống gặp sự cố hiển thị</h2>
          <div className="bg-white p-4 rounded-xl border border-red-100 shadow-sm max-w-lg mb-6">
            <p className="text-red-600 font-mono text-xs break-all leading-relaxed">
              {this.state.error?.toString()}
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-xl font-bold shadow-lg shadow-red-200 hover:bg-red-700 transition-all active:scale-95"
          >
            <RefreshCw className="w-5 h-5" />
            THỬ TẢI LẠI TRANG
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
