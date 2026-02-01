import { Suspense, lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./layouts/MainLayout.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { useAuth } from "./contexts/AuthContext.jsx";

// [OPTIMIZATION] Lazy load pages to reduce initial bundle size
const Dashboard = lazy(() => import("./pages/DashboardV2.jsx"));
const Events = lazy(() => import("./pages/Events.jsx"));
const EventDetail = lazy(() => import("./pages/EventDetail.jsx"));
const MapPage = lazy(() => import("./pages/MapPage.jsx"));
const About = lazy(() => import("./pages/About.jsx"));
const Terms = lazy(() => import("./pages/Terms.jsx"));
const Privacy = lazy(() => import("./pages/Privacy.jsx"));
const AdminSkipLogs = lazy(() => import("./pages/AdminSkipLogs.jsx"));
const AdminReports = lazy(() => import("./pages/AdminReports.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));
const RegisterPage = lazy(() => import("./pages/RegisterPage.jsx"));
const RescuePage = lazy(() => import("./pages/Rescue.jsx"));
const CrawlerDashboard = lazy(() => import("./pages/CrawlerDashboard.jsx"));
const ChangePasswordPage = lazy(() => import("./pages/ChangePasswordPage.jsx"));

// Simple loading fallback
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
  </div>
);


function ProtectedRoute({ children, roleRequired }) {
  const { user, loading } = useAuth();

  if (loading) return <PageLoader />;
  
  const isAuthenticated = !!(user && user.role && user.role !== "guest");
  const currentRole = (user?.role || "").trim().toLowerCase();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: window.location.pathname + window.location.search }} />;
  }

  // [ROLE CHECK] Robust comparison
  if (roleRequired) {
     const required = roleRequired.trim().toLowerCase();
     if (currentRole !== required) {
        return <Navigate to="/login" replace />;
     }
  }

  return children;
}

export default function App() {
  return (
    <MainLayout>
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/events" element={<Events />} />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/about" element={<About />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
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
            <Route path="/admin/crawler" element={
              <ProtectedRoute roleRequired="admin">
                <CrawlerDashboard />
              </ProtectedRoute>
            } />

            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/change-password" element={
              <ProtectedRoute>
                <ChangePasswordPage />
              </ProtectedRoute>
            } />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </MainLayout>
  );
}
