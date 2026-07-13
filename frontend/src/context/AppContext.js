import React, { createContext, useContext, useState, useEffect } from 'react';
import { DEFAULT_TARGETS, HISTORY as INITIAL_HISTORY, generateExtractionResults } from '../mock';

const AppContext = createContext(null);

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};

export const AppProvider = ({ children }) => {
  const [product, setProduct] = useState('prolomet xl 25');
  const [targets, setTargets] = useState(() => {
    try {
      const saved = localStorage.getItem('ps.targets');
      return saved ? JSON.parse(saved) : DEFAULT_TARGETS;
    } catch { return DEFAULT_TARGETS; }
  });
  const [history, setHistory] = useState(() => {
    try {
      const saved = localStorage.getItem('ps.history');
      return saved ? JSON.parse(saved) : INITIAL_HISTORY;
    } catch { return INITIAL_HISTORY; }
  });

  useEffect(() => {
    localStorage.setItem('ps.targets', JSON.stringify(targets));
  }, [targets]);
  useEffect(() => {
    localStorage.setItem('ps.history', JSON.stringify(history));
  }, [history]);

  const toggleTarget = (id) => {
    setTargets((prev) => prev.map((t) => (t.id === id ? { ...t, selected: !t.selected } : t)));
  };

  const setAllTargets = (selected) => {
    setTargets((prev) => prev.map((t) => ({ ...t, selected })));
  };

  const addTarget = (t) => setTargets((prev) => [...prev, { ...t, id: 't' + Date.now(), selected: true }]);
  const removeTarget = (id) => setTargets((prev) => prev.filter((t) => t.id !== id));

  const runExtraction = async () => {
    const active = targets.filter((t) => t.selected);
    const results = generateExtractionResults(product.toUpperCase(), active);
    const found = results.filter((r) => r.status === 'IN_STOCK').length;
    const oos = results.filter((r) => r.status === 'OUT_OF_STOCK').length;
    const err = results.filter((r) => r.status === 'ERROR').length;
    const entry = {
      id: 'h' + Date.now(),
      product: product.toUpperCase(),
      timestamp: new Date().toISOString(),
      duration: (Math.random() * 4 + 2).toFixed(1) + 's',
      targetsRun: active.length,
      found,
      outOfStock: oos,
      errors: err,
      status: err > 0 ? 'PARTIAL' : 'COMPLETED',
      results,
    };
    setHistory((prev) => [entry, ...prev]);
    return entry;
  };

  return (
    <AppContext.Provider
      value={{ product, setProduct, targets, toggleTarget, setAllTargets, addTarget, removeTarget, history, runExtraction }}
    >
      {children}
    </AppContext.Provider>
  );
};
