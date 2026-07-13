import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { useApp } from '../context/AppContext';
import { CheckCircle2, XCircle, AlertOctagon, Loader2, Zap, Copy, Download } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_META = {
  IN_STOCK: { label: 'IN STOCK', Icon: CheckCircle2, tone: 'text-neutral-950' },
  OUT_OF_STOCK: { label: 'OUT OF STOCK', Icon: XCircle, tone: 'text-neutral-500' },
  ERROR: { label: 'ERROR', Icon: AlertOctagon, tone: 'text-neutral-500' },
};

const ExtractionModal = ({ open, onOpenChange }) => {
  const { product, targets, runExtraction } = useApp();
  const [phase, setPhase] = useState('idle'); // idle | running | done
  const [entry, setEntry] = useState(null);
  const [progressIdx, setProgressIdx] = useState(0);

  const active = useMemo(() => targets.filter((t) => t.selected), [targets]);

  useEffect(() => {
    if (!open) {
      setPhase('idle');
      setEntry(null);
      setProgressIdx(0);
      return;
    }
    setPhase('running');
    setProgressIdx(0);
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setProgressIdx(i);
      if (i >= active.length) {
        clearInterval(timer);
      }
    }, 380);

    const total = Math.max(active.length * 380 + 400, 1200);
    const finish = setTimeout(async () => {
      const result = await runExtraction();
      setEntry(result);
      setPhase('done');
    }, total);

    return () => {
      clearInterval(timer);
      clearTimeout(finish);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const exportCsv = () => {
    if (!entry) return;
    const rows = [
      ['product', 'target', 'portal', 'status', 'price', 'mrp', 'stock', 'pack', 'response_ms', 'url'],
      ...entry.results.map((r) => [
        entry.product, r.targetName, r.portal, r.status, r.price || '', r.mrp || '', r.stock, r.pack || '', r.responseMs, r.url,
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${entry.product.replace(/\s+/g, '_').toLowerCase()}_${entry.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast('CSV downloaded');
  };

  const copyJson = () => {
    if (!entry) return;
    navigator.clipboard.writeText(JSON.stringify(entry, null, 2));
    toast('JSON copied');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-neutral-950 rounded-sm p-0 gap-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-neutral-200">
          <DialogTitle className="text-[20px] font-extrabold mono-track uppercase leading-none">
            {phase === 'running' ? 'RUNNING EXTRACTION' : 'EXTRACTION RESULTS'}
          </DialogTitle>
          <p className="mt-2 text-[11px] text-neutral-500 mono-track-wide font-medium">
            PRODUCT · {product.toUpperCase()}
          </p>
        </DialogHeader>

        {/* Running */}
        {phase === 'running' && (
          <div className="px-6 py-5">
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="w-5 h-5 animate-spin" strokeWidth={2} />
              <span className="text-[12px] mono-track-wide font-semibold">
                {Math.min(progressIdx, active.length)}/{active.length} TARGETS PROCESSED
              </span>
            </div>
            <div className="h-1 bg-neutral-200 rounded-sm overflow-hidden">
              <div
                className="h-full bg-neutral-950 transition-all duration-300"
                style={{ width: `${(Math.min(progressIdx, active.length) / active.length) * 100}%` }}
              />
            </div>
            <ul className="mt-5 space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {active.map((t, i) => {
                const state = i < progressIdx ? 'done' : i === progressIdx ? 'active' : 'pending';
                return (
                  <li key={t.id} className="flex items-center gap-3 py-1.5">
                    <div className="w-5 h-5 flex items-center justify-center shrink-0">
                      {state === 'done' && <CheckCircle2 className="w-4 h-4" strokeWidth={2} />}
                      {state === 'active' && <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2} />}
                      {state === 'pending' && <div className="w-2 h-2 rounded-full bg-neutral-300" />}
                    </div>
                    <span className={`text-[13px] mono-track-tight font-semibold uppercase truncate ${state === 'pending' ? 'text-neutral-400' : 'text-neutral-950'}`}>
                      {t.name}
                    </span>
                    <span className="ml-auto text-[10px] text-neutral-500 mono-track-wide">{t.portal}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Done */}
        {phase === 'done' && entry && (
          <div className="px-6 py-5">
            {/* Summary */}
            <div className="grid grid-cols-4 gap-2 mb-5">
              <SummaryStat label="TARGETS" value={entry.targetsRun} />
              <SummaryStat label="IN STOCK" value={entry.found} strong />
              <SummaryStat label="OUT" value={entry.outOfStock} />
              <SummaryStat label="TIME" value={entry.duration} />
            </div>

            {/* Results */}
            <ul className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {entry.results.map((r) => {
                const meta = STATUS_META[r.status];
                const { Icon } = meta;
                return (
                  <li key={r.targetId} className="border border-neutral-300 rounded-sm p-3">
                    <div className="flex items-start gap-3">
                      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${meta.tone}`} strokeWidth={2} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-extrabold mono-track-tight uppercase truncate">{r.targetName}</span>
                          <span className="text-[9px] mono-track-wide font-semibold border border-neutral-300 rounded-sm px-1.5 py-0.5 text-neutral-500">
                            {r.portal}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] mono-track-tight text-neutral-500">
                          {r.status === 'IN_STOCK' && (
                            <span>₹{r.price} · MRP ₹{r.mrp} · STOCK {r.stock} · PACK {r.pack}</span>
                          )}
                          {r.status === 'OUT_OF_STOCK' && <span>PRODUCT NOT AVAILABLE</span>}
                          {r.status === 'ERROR' && <span>PORTAL TIMEOUT</span>}
                        </div>
                      </div>
                      <span className="text-[10px] text-neutral-400 mono-track-tight tabular-nums shrink-0">
                        {r.responseMs}ms
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>

            {/* Actions */}
            <div className="mt-5 grid grid-cols-2 gap-2">
              <button
                onClick={copyJson}
                className="h-11 border border-neutral-300 hover:border-neutral-950 rounded-sm flex items-center justify-center gap-2 text-[11px] mono-track-wide font-semibold press"
              >
                <Copy className="w-3.5 h-3.5" strokeWidth={2} /> COPY JSON
              </button>
              <button
                onClick={exportCsv}
                className="h-11 bg-neutral-950 hover:bg-neutral-800 text-white rounded-sm flex items-center justify-center gap-2 text-[11px] mono-track-wide font-semibold press"
              >
                <Download className="w-3.5 h-3.5" strokeWidth={2} /> EXPORT CSV
              </button>
            </div>
          </div>
        )}

        {/* Idle fallback */}
        {phase === 'idle' && (
          <div className="px-6 py-10 flex items-center justify-center text-neutral-500">
            <Zap className="w-5 h-5 mr-2" /> READY
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

const SummaryStat = ({ label, value, strong }) => (
  <div className={`border rounded-sm px-2.5 py-2.5 ${strong ? 'bg-neutral-950 text-white border-neutral-950' : 'border-neutral-300'}`}>
    <div className="text-[18px] font-extrabold mono-track-tight tabular-nums leading-none">{value}</div>
    <div className={`mt-1.5 text-[9px] mono-track-wide font-medium ${strong ? 'text-neutral-300' : 'text-neutral-500'}`}>{label}</div>
  </div>
);

export default ExtractionModal;
