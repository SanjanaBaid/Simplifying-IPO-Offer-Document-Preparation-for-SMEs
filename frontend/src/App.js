import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import TopNav from "./components/TopNav";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Intake from "./pages/Intake";
import Drafting from "./pages/Drafting";
import Consistency from "./pages/Consistency";
import Audit from "./pages/Audit";
import Handoff from "./pages/Handoff";
import BankerDashboard from "./pages/BankerDashboard";
import BankerMandate from "./pages/BankerMandate";
import "./App.css";

function RequireAuth({ children, role }) {
  const { token, promoter, loading } = useAuth();
  if (loading) {
    return <div className="auth-loading">Loading…</div>;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  if (role && promoter && promoter.role !== role) {
    return <Navigate to={promoter.role === "banker" ? "/banker/dashboard" : "/dashboard"} replace />;
  }
  return children;
}

function AppShell({ children }) {
  return (
    <div className="app-shell">
      <TopNav />
      <main className="app-main">{children}</main>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/dashboard"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Dashboard />
            </AppShell>
          </RequireAuth>
        }
      />

      <Route
        path="/company/:companyId/intake"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Intake />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/drafting"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Drafting />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/consistency"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Consistency />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/audit"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Audit />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/handoff"
        element={
          <RequireAuth role="promoter">
            <AppShell>
              <Handoff />
            </AppShell>
          </RequireAuth>
        }
      />

      <Route
        path="/banker/dashboard"
        element={
          <RequireAuth role="banker">
            <AppShell>
              <BankerDashboard />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/banker/mandates/:companyId"
        element={
          <RequireAuth role="banker">
            <AppShell>
              <BankerMandate />
            </AppShell>
          </RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}