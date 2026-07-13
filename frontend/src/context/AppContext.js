import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { TargetsAPI, HistoryAPI, ExtractAPI } from '../lib/api';

const AppContext = createContext(null);

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};

export const AppProvider = ({ children }) => {
  const [product, setProduct] = useState('prolomet xl 25');
  const [targets, setTargets] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshTargets = useCallback(async () => {
    const data = await TargetsAPI.list();
    setTargets(data);
  }, []);

  const refreshHistory = useCallback(async () => {
    const data = await HistoryAPI.list();
    setHistory(data);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        await Promise.all([refreshTargets(), refreshHistory()]);
      } catch (e) {
        console.error(e);
        setError('Failed to load data');
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshTargets, refreshHistory]);

  const toggleTarget = async (id) => {
    const target = targets.find((t) => t.id === id);
    if (!target) return;
    // Optimistic update
    setTargets((prev) => prev.map((t) => (t.id === id ? { ...t, selected: !t.selected } : t)));
    try {
      await TargetsAPI.update(id, { selected: !target.selected });
    } catch (e) {
      // Revert on error
      setTargets((prev) => prev.map((t) => (t.id === id ? { ...t, selected: target.selected } : t)));
    }
  };

  const setAllTargets = async (selected) => {
    setTargets((prev) => prev.map((t) => ({ ...t, selected })));
    try { await TargetsAPI.bulkSelect(selected); } catch (e) { console.error(e); }
  };

  const addTarget = async (t) => {
    const created = await TargetsAPI.create(t);
    setTargets((prev) => [...prev, created]);
    return created;
  };

  const removeTarget = async (id) => {
    setTargets((prev) => prev.filter((t) => t.id !== id));
    try { await TargetsAPI.remove(id); } catch (e) { console.error(e); }
  };

  const runExtraction = async () => {
    const active = targets.filter((t) => t.selected).map((t) => t.id);
    const entry = await ExtractAPI.run(product, active);
    setHistory((prev) => [entry, ...prev]);
    return entry;
  };

  const getHistoryDetail = async (id) => {
    return HistoryAPI.get(id);
  };

  return (
    <AppContext.Provider
      value={{
        product, setProduct,
        targets, toggleTarget, setAllTargets, addTarget, removeTarget,
        history, runExtraction, getHistoryDetail,
        loading, error,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
