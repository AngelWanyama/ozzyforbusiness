import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import api from '../api/client';

interface AuthState {
  isAuthenticated: boolean;
  loading: boolean;
  plan: any | null;
  usage: any | null;
  login: (phone: string, code: string) => Promise<void>;
  requestOTP: (phone: string) => Promise<any>;
  logout: () => void;
  fetchUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [plan, setPlan] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchUserData = useCallback(async () => {
    try {
      const [p, u] = await Promise.all([api.getUserPlan(), api.getUserUsage()]);
      setPlan(p); setUsage(u);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (api.getToken()) fetchUserData().finally(() => setLoading(false));
    else setLoading(false);
  }, [fetchUserData]);

  const login = async (phone: string, code: string) => {
    await api.verifyOTP(phone, code);
    await fetchUserData();
  };

  const logout = () => { api.clearToken(); setPlan(null); setUsage(null); };

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!api.getToken(), loading, plan, usage, login, requestOTP: api.requestOTP.bind(api), logout, fetchUserData }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}