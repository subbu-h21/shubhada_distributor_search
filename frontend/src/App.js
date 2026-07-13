import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import SearchPage from './pages/SearchPage';
import PortalsPage from './pages/PortalsPage';
import HistoryPage from './pages/HistoryPage';
import { AppProvider } from './context/AppContext';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <div className="App">
      <AppProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/search" replace />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/portals" element={<PortalsPage />} />
              <Route path="/history" element={<HistoryPage />} />
            </Routes>
          </Layout>
        </BrowserRouter>
        <Toaster position="top-center" />
      </AppProvider>
    </div>
  );
}

export default App;
