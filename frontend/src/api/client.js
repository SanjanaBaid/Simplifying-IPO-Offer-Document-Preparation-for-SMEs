import axios from "axios";


export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});


apiClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("sherpa.authToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
