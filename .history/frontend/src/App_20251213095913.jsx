import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Events from "./pages/Events.jsx";
import EventDetail from "./pages/EventDetail.jsx";
import About from "./pages/About.jsx";

function TopNav() {
  const link = ({ isActive }) =>
    "px-3 py-2 rounded-lg text-sm font-medium " +
    (isActive
      ? "bg-blue-100 text-blue-900"
      : "hover:bg-gray-100 text-gray-700");
  return (
    <div className="sticky top-0 z-10 border-b border-gray-200 bg-white/80 backdrop-blur">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500" />
          <div>
            <div className="text-base font-semibold leading-tight text-gray-900">
              Viet Disaster Watch
            </div>
            <div className="text-xs text-gray-500">
              Tin thiên tai • Phân loại • Đối chiếu đa nguồn
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <NavLink to="/" className={link} end>
            Dashboard
          </NavLink>
          <NavLink to="/events" className={link}>
            Sự kiện
          </NavLink>
          <NavLink to="/about" className={link}>
            Giới thiệu
          </NavLink>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:id" element={<EventDetail />} />
        <Route path="/about" element={<About />} />
      </Routes>
      <footer className="border-t border-gray-200 mt-12 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-8 text-xs text-gray-600">
          Dữ liệu tổng hợp từ 12 nguồn báo chính thống (metadata + link). Không
          đăng lại toàn văn.
        </div>
      </footer>
    </div>
  );
}
