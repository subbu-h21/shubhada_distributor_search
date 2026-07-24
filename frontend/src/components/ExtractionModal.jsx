import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { useApp } from '../context/AppContext';
import { CheckCircle2, XCircle, AlertOctagon, Loader2, Zap, Copy, Download, KeyRound, ImageIcon } from 'lucide-react';
import { toast } from 'sonner';
import { screenshotUrl } from '../lib/api';
import ResultCard from './ResultCard';
import ExtractionProgress from './ExtractionProgress';
import ResultFilters from './ResultFilters';
import { explodeResults } from '../lib/resultUtils';

const ExtractionModal = ({ open, onOpenChange }) => {
  const { product, quantity, distributors, runExtraction } = useApp();
  const [phase, setPhase] = useState('idle');
  const [entry, setEntry] = useState(null);
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const active = useMemo(() => distributors.filter((t) => t.selected), [distributors]);

  useEffect(() => {
    if (!open) {
      setPhase('idle'); setEntry(null); setError(null); setElapsed(0);
      return;
    }
    setPhase('running'); setEntry(null); setError(null); setElapsed(0);
    (async () => {
      try {
        const result = await runExtraction({ onProgress: setElapsed });
        setEntry(result);
        setPhase('done');
      } catch (e) {
        console.error(e);
        setError(e?.response?.data?.detail || e.message || 'Extraction failed');
        setPhase('error');
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const exportCsv = () => {
    if (!entry) return;
    const rows = [
      ['product', 'distributor', 'portal', 'status', 'detail', 'seller', 'matched', 'manufacturer', 'pack', 'mrp', 'ptr', 'available_qty', 'scheme', 'batch', 'expiry'],
    ];
    for (const r of entry.results || []) {
      if (!r.items || r.items.length === 0) {
        rows.push([entry.product, r.targetName, r.portal, r.status, r.detail || '', '', '', '', '', '', '', '', '', '', '']);
      } else {
        for (const it of r.items) {
          rows.push([entry.product, r.targetName, r.portal, r.status, r.detail || '', it.seller || '', it.matched_name || '', it.manufacturer || '', it.pack || '', it.mrp || '', it.ptr || '', it.available_qty || '', it.scheme || '', it.batch || '', it.expiry || '']);
        }
      }
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${entry.product.replace(/\s+/g, '_').toLowerCase()}_${entry.id}.csv`;
    a.click(); URL.revokeObjectURL(url);
    toast('CSV downloaded');
  };

  const copyJson = () => {
    if (!entry) return;
    const text = JSON.stringify(entry, null, 2);
    // Try legacy textarea copy FIRST — iframes commonly block the modern
    // Clipboard API via Permissions Policy, and calling it can throw
    // synchronously (not just reject the promise).
    const legacyCopy = () => {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.top = '-1000px';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        if (ok) { toast('JSON copied'); return true; }
      } catch (e) {}
      return false;
    };
    if (legacyCopy()) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
          .then(() => toast('JSON copied'))
          .catch(() => toast.error('Copy blocked — please long-press to select the JSON'));
        return;
      }
    } catch (e) {}
    toast.error('Copy blocked — please long-press to select the JSON');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl border-emerald-600 rounded-sm p-0 gap-0 max-h-[92vh] overflow-hidden flex flex-col">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-neutral-200 shrink-0">
          <DialogTitle className="text-[20px] font-extrabold mono-track uppercase leading-none">
            {phase === 'running' ? 'RUNNING EXTRACTION' : phase === 'error' ? 'EXTRACTION FAILED' : 'EXTRACTION RESULTS'}
          </DialogTitle>
          <p className="mt-2 text-[11px] text-neutral-500 mono-track-wide font-medium">
            {product.toUpperCase()}{quantity ? ` · QTY ${quantity}` : ''} · {active.length} DISTRIBUTOR{active.length !== 1 ? 'S' : ''}
          </p>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {phase === 'running' && (
            <ExtractionProgress
              distributors={active}
              resultsByTargetId={{}}
              product={product}
              quantity={quantity}
            />
          )}

          {phase === 'error' && (
            <div className="px-6 py-10 flex flex-col items-center justify-center min-h-[220px]">
              <AlertOctagon className="w-8 h-8 mb-3" strokeWidth={1.6} />
              <p className="text-[13px] mono-track-wide font-bold">EXTRACTION FAILED</p>
              <p className="mt-2 text-[11px] mono-track-tight text-neutral-500 max-w-md text-center">{error}</p>
            </div>
          )}

          {phase === 'done' && entry && (
            <div className="px-6 py-5">
              <div className="grid grid-cols-4 gap-2 mb-5">
                <Stat label="RUN" value={entry.targetsRun} />
                <Stat label="FOUND" value={entry.found} strong />
                <Stat label="NOT FOUND" value={entry.notFound ?? entry.outOfStock ?? 0} />
                <Stat label="TIME" value={entry.duration} />
              </div>

              <ResultFilters results={explodeResults(entry.results || [])}>
                {(shown) => (
                  <ul className="space-y-3">
                    {shown.map((r) => (
                      <li key={r.targetId}>
                        <ResultCard
                          result={r}
                          requestedQty={entry.quantity}
                          historyId={entry.id}
                          onUpdate={(nr) => {
                            setEntry((prev) => prev ? {
                              ...prev,
                              // Update the underlying (aggregator) row — the
                              // explode helper will re-expand on next render.
                              results: prev.results.map((x) => x.targetId === (nr._parentTargetId || nr.targetId) ? nr : x),
                            } : prev);
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </ResultFilters>

              <div className="mt-5 grid grid-cols-2 gap-2">
                <button onClick={copyJson} className="h-11 border border-neutral-300 hover:border-emerald-600 rounded-sm flex items-center justify-center gap-2 text-[11px] mono-track-wide font-semibold press">
                  <Copy className="w-3.5 h-3.5" /> COPY JSON
                </button>
                <button onClick={exportCsv} className="h-11 bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm flex items-center justify-center gap-2 text-[11px] mono-track-wide font-semibold press">
                  <Download className="w-3.5 h-3.5" /> EXPORT CSV
                </button>
              </div>
            </div>
          )}

          {phase === 'idle' && (
            <div className="px-6 py-10 flex items-center justify-center text-neutral-500">
              <Zap className="w-5 h-5 mr-2" /> READY
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

const Stat = ({ label, value, strong }) => (
  <div className={`border rounded-sm px-2.5 py-2.5 ${strong ? 'bg-emerald-600 text-white border-emerald-600' : 'border-neutral-300'}`}>
    <div className="text-[18px] font-extrabold mono-track-tight tabular-nums leading-none">{value}</div>
    <div className={`mt-1.5 text-[9px] mono-track-wide font-medium ${strong ? 'text-neutral-300' : 'text-neutral-500'}`}>{label}</div>
  </div>
);

export default ExtractionModal;
