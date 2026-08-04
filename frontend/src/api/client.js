import axios from "axios";

// Step 6 — real API wiring.
//
// Base URL is configurable via REACT_APP_API_BASE_URL (e.g. for the Render
// deployment); it falls back to the local FastAPI dev server from Step 1.
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export default apiClient;
