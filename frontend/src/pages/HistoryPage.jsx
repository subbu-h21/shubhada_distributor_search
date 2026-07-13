import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { CheckCircle2, AlertTriangle, ChevronRight, Package } from 'lucide-react';
import HistoryDetail from '../components/HistoryDetail';

function formatDate(iso) {
  const d = new Date(iso);
  const dd = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase();
  const tt = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  return `${dd} · ${tt}`;
}

const HistoryPage = () => {
  const { history } = useApp();
  const [selected, setSelected] = useState(null);

  return (
    <div className="pt-3">
      <div className="grid grid-cols-3 gap-2 mb-5">
        <Stat label="TOTAL RUNS" value={history.length} />
        <Stat label="AVG TARGETS" value={Math.round(history.reduce((a, h) => a + h.targetsRun, 0) / Math.max(history.length, 1))} />
        <Stat label="FOUND" value={history.reduce((a, h) => a + h.found, 0)} />
      </div>

      <ul className="space-y-2.5">
        {history.map((h) => (
          <li key={h.id}>
            <button
              type="button"
              onClick={() => setSelected(h)}
              className="w-full text-left border border-neutral-300 rounded-sm px-4 py-3.5 card-hover bg-white flex items-center gap-3"
            >
              <div className="w-9 h-9 shrink-0 border border-neutral-950 rounded-sm flex items-center justify-center">
                <Package className="w-4 h-4" strokeWidth={1.8} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-extrabold mono-track-tight uppercase truncate">{h.product}</span>
                </div>
                <div className="mt-1 text-[11px] text-neutral-500 flex items-center gap-2 mono-track-tight">
                  <span>{formatDate(h.timestamp)}</span>
                  <span className="w-1 h-1 bg-neutral-300 rounded-full" />
                  <span>{h.duration}</span>
                  <span className="w-1 h-1 bg-neutral-300 rounded-full" />
                  <span>{h.targetsRun} TARGETS</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 text-[11px] font-semibold mono-track-tight">
                  {h.status === 'COMPLETED' ? (
                    <CheckCircle2 className="w-4 h-4" strokeWidth={1.8} />
                  ) : (
                    <AlertTriangle className="w-4 h-4" strokeWidth={1.8} />
                  )}
                  <span>{h.found}/{h.targetsRun}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-neutral-400" />
              </div>
            </button>
          </li>
        ))}
      </ul>

      <HistoryDetail entry={selected} onClose={() => setSelected(null)} />
    </div>
  );
};

const Stat = ({ label, value }) => (
  <div className="border border-neutral-300 rounded-sm px-3 py-3">
    <div className="text-[22px] font-extrabold mono-track-tight tabular-nums leading-none">{value}</div>
    <div className="mt-2 text-[9px] text-neutral-500 mono-track-wide font-medium">{label}</div>
  </div>
);

export default HistoryPage;
