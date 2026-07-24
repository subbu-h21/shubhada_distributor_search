import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { DistributorsAPI, HistoryAPI, ExtractAPI } from '../lib/api';

const AppContext = createContext(null);

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};

export const AppProvider = ({ children }) => {
  const [product, setProduct] = useState('prolomet xl 25');
  const [quantity, setQuantity] = useState('10');
  const [distributors, setDistributors] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshDistributors = useCallback(async () => {
    const data = await DistributorsAPI.list();
    setDistributors(data);
  }, []);

  const refreshHistory = useCallback(async () => {
    const data = await HistoryAPI.list();
    setHistory(data);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        await Promise.all([refreshDistributors(), refreshHistory()]);
      } catch (e) {
        console.error(e);
        setError('Failed to load data');
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshDistributors, refreshHistory]);

  const toggleDistributor = async (id) => {
    const d = distributors.find((t) => t.id === id);
    if (!d) return;
    setDistributors((prev) => prev.map((t) => (t.id === id ? { ...t, selected: !t.selected } : t)));
    try { await DistributorsAPI.update(id, { selected: !d.selected }); }
    catch (e) { setDistributors((prev) => prev.map((t) => (t.id === id ? { ...t, selected: d.selected } : t))); }
  };

  const setAllSelected = async (selected) => {
    setDistributors((prev) => prev.map((t) => ({ ...t, selected })));
    try { await DistributorsAPI.bulkSelect(selected); } catch (e) { console.error(e); }
  };

  const addDistributor = async (t) => {
    const created = await DistributorsAPI.create(t);
    setDistributors((prev) => [...prev, created]);
    return created;
  };

  const updateDistributor = async (id, patch) => {
    const updated = await DistributorsAPI.update(id, patch);
    setDistributors((prev) => prev.map((t) => (t.id === id ? updated : t)));
    return updated;
  };

  const removeDistributor = async (id) => {
    setDistributors((prev) => prev.filter((t) => t.id !== id));
    try { await DistributorsAPI.remove(id); } catch (e) { console.error(e); }
  };

  const runExtraction = async ({ onProgress } = {}) => {
    const ids = distributors.filter((t) => t.selected).map((t) => t.id);
    const entry = await ExtractAPI.run(product, quantity, ids, { onProgress });
    setHistory((prev) => [entry, ...prev]);
    return entry;
  };

  const getHistoryDetail = async (id) => HistoryAPI.get(id);

  return (
    <AppContext.Provider
      value={{
        product, setProduct,
        quantity, setQuantity,
        distributors,
        toggleDistributor, setAllSelected,
        addDistributor, updateDistributor, removeDistributor,
        history, runExtraction, getHistoryDetail,
        loading, error,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
