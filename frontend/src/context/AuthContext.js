import { createContext, useCallback, useContext, useEffect, useState } from "react";
import apiClient from "../api/client";

const TOKEN_KEY = "sherpa.authToken";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY) || "");
  const [promoter, setPromoter] = useState(null);
  const [loading, setLoading] = useState(!!token);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient
      .get("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setPromoter(data))
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY);
        setToken("");
        setPromoter(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const persistSession = useCallback((newToken, newPromoter) => {
    window.localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setPromoter(newPromoter);
  }, []);

  const signup = useCallback(
    async ({ fullName, email, password, merchantBankingFirm }) => {
      const { data } = await apiClient.post("/auth/signup", {
        full_name: fullName,
        email,
        password,
        merchant_banking_firm: merchantBankingFirm || null,
      });
      persistSession(data.token, data.promoter);
      return data.promoter;
    },
    [persistSession]
  );

  const login = useCallback(
    async ({ email, password }) => {
      const { data } = await apiClient.post("/auth/login", { email, password });
      persistSession(data.token, data.promoter);
      return data.promoter;
    },
    [persistSession]
  );

  const logout = useCallback(async () => {
    try {
      await apiClient.post(
        "/auth/logout",
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch {
      // Session may already be gone server-side — clear locally regardless.
    }
    window.localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setPromoter(null);
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, promoter, loading, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}