import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState(null);
  const [usage, setUsage] = useState(null);

  const fetchUserData = useCallback(async () => {
    try {
      const [planData, usageData] = await Promise.all([
        api.getUserPlan(),
        api.getUserUsage(),
      ]);
      setPlan(planData);
      setUsage(usageData);
    } catch (err) {
      console.error('Failed to fetch user data:', err);
    }
  }, []);

  useEffect(() => {
    const token = api.getToken();
    if (token) {
      fetchUserData().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchUserData]);

  const login = async (phoneNumber, code) => {
    const data = await api.verifyOTP(phoneNumber, code);
    await fetchUserData();
    return data;
  };

  const requestOTP = async (phoneNumber) => {
    return api.requestOTP(phoneNumber);
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
    setPlan(null);
    setUsage(null);
  };

  const isAuthenticated = !!api.getToken();

  return (
    <AuthContext.Provider value={{
      user,
      plan,
      usage,
      loading,
      login,
      requestOTP,
      logout,
      isAuthenticated,
      fetchUserData,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}