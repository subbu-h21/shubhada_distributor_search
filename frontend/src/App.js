import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import SearchPage from './pages/SearchPage';
import PortalsPage from './pages/PortalsPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Toaster } from './components/ui/sonner';
import { Loader2 } from 'lucide-react';

const AppShell = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-neutral-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-[11px] mono-track-wide">LOADING</span>
      </div>
    );
  }

  if (!isAuthenticated) return <LoginPage />;

  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/portals" element={<PortalsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="*" element={<Navigate to="/search" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AppProvider>
  );
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <AppShell />
      </AuthProvider>
      <Toaster position="top-center" />
    </div>
  );
}

export default App;
