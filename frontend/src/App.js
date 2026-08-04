import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Intake from "./pages/Intake";
import Drafting from "./pages/Drafting";
import Consistency from "./pages/Consistency";
import Audit from "./pages/Audit";
import Handoff from "./pages/Handoff";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <Routes>
          <Route path="/" element={<Navigate to="/intake" replace />} />
          <Route path="/intake" element={<Intake />} />
          <Route path="/drafting" element={<Drafting />} />
          <Route path="/consistency" element={<Consistency />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/handoff" element={<Handoff />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
