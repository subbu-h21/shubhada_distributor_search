import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../lib/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

const TOKEN_KEY = 'ps.token';
const USER_KEY = 'ps.user';

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (!token) { setLoading(false); return; }
      try {
        const { data } = await axios.get(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(data);
        localStorage.setItem(USER_KEY, JSON.stringify(data));
      } catch (e) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken(null); setUser(null);
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (username, password) => {
    const { data } = await axios.post(`${API_BASE}/auth/login`, { username, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.token); setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null); setUser(null);
  };

  const changePassword = async (currentPassword, newPassword) =>
    axios.post(
      `${API_BASE}/auth/change-password`,
      { current_password: currentPassword, new_password: newPassword },
      { headers: { Authorization: `Bearer ${token}` } },
    ).then((r) => r.data);

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated: !!token && !!user, login, logout, changePassword, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
