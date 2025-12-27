import { Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import Dashboard from "./pages/DashboardV2.jsx";
import Events from "./pages/Events.jsx";
import EventDetail from "./pages/EventDetail.jsx";
import MapPage from "./pages/MapPage.jsx";
import About from "./pages/About.jsx";
import AdminSkipLogs from "./pages/AdminSkipLogs.jsx";
import AdminReports from "./pages/AdminReports.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import RescuePage from "./pages/Rescue.jsx";
import { Navigate } from "react-router-dom";

function ProtectedRoute({ children, roleRequired }) {
  const storedUser = localStorage.getItem("user");
  let user = null;
  if (storedUser) {
    try {
      user = JSON.parse(storedUser);
    } catch (e) {
      user = null;
    }
  }

  if (!user || (roleRequired && user.role !== roleRequired)) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <MainLayout>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/events" element={<Events />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/about" element={<About />} />
          <Route path="/rescue" element={<RescuePage />} />
          <Route path="/admin/logs" element={
            <ProtectedRoute roleRequired="admin">
              <AdminSkipLogs />
            </ProtectedRoute>
          } />
          <Route path="/admin/reports" element={
            <ProtectedRoute roleRequired="admin">
              <AdminReports />
            </ProtectedRoute>
          } />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </ErrorBoundary>
    </MainLayout>
  );
}
