import { createContext, useContext, useEffect, useState } from "react";
import api, { tokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, if we have a token, find out who it belongs to.
  useEffect(() => {
    if (!tokens.getAccess()) {
      setLoading(false);
      return;
    }
    api
      .get("/auth/me/")
      .then((response) => setUser(response.data))
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const { data } = await api.post("/auth/login/", { email, password });
    tokens.save(data);
    const me = await api.get("/auth/me/");
    setUser(me.data);
  }

  async function register(fields) {
    await api.post("/auth/register/", fields);
    await login(fields.email, fields.password);
  }

  async function logout() {
    try {
      await api.post("/auth/logout/", { refresh: tokens.getRefresh() });
    } catch {
      // Even if the server call fails, the user is logged out locally.
    }
    tokens.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
