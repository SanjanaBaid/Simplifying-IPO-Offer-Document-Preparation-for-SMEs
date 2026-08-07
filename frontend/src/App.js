import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import TopNav from "./components/TopNav";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Intake from "./pages/Intake";
import Drafting from "./pages/Drafting";
import Consistency from "./pages/Consistency";
import Audit from "./pages/Audit";
import Handoff from "./pages/Handoff";
import "./App.css";

function RequireAuth({ children }) {
  const { token, loading } = useAuth();
  if (loading) {
    return <div className="auth-loading">Loading…</div>;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
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
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <AppShell>
              <Dashboard />
            </AppShell>
          </RequireAuth>
        }
      />

      <Route
        path="/company/:companyId/intake"
        element={
          <RequireAuth>
            <AppShell>
              <Intake />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/drafting"
        element={
          <RequireAuth>
            <AppShell>
              <Drafting />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/consistency"
        element={
          <RequireAuth>
            <AppShell>
              <Consistency />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/audit"
        element={
          <RequireAuth>
            <AppShell>
              <Audit />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/company/:companyId/handoff"
        element={
          <RequireAuth>
            <AppShell>
              <Handoff />
            </AppShell>
          </RequireAuth>
        }
      />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
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