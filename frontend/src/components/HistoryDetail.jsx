import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import ResultCard from './ResultCard';
import ResultFilters from './ResultFilters';
import { explodeResults } from '../lib/resultUtils';

const HistoryDetail = ({ entry, onClose }) => {
  const open = !!entry;
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl border-emerald-600 rounded-sm p-0 gap-0 max-h-[92vh] overflow-hidden flex flex-col">
        {entry && (
          <>
            <DialogHeader className="px-6 pt-6 pb-4 border-b border-neutral-200 shrink-0">
              <DialogTitle className="text-[20px] font-extrabold mono-track uppercase leading-none">{entry.product}</DialogTitle>
              <p className="mt-2 text-[11px] text-neutral-500 mono-track-wide font-medium">
                {new Date(entry.timestamp).toLocaleString()} · {entry.duration} · {entry.status}
                {entry.quantity ? ` · QTY ${entry.quantity}` : ''}
              </p>
            </DialogHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="grid grid-cols-4 gap-2 mb-5">
                <MiniStat label="RUN" value={entry.targetsRun} />
                <MiniStat label="FOUND" value={entry.found} strong />
                <MiniStat label="NOT FOUND" value={entry.notFound ?? entry.outOfStock ?? 0} />
                <MiniStat label="ERRORS" value={(entry.errors ?? 0) + (entry.loginFailed ?? 0)} />
              </div>

              {entry.results && entry.results.length > 0 ? (
                <ResultFilters results={explodeResults(entry.results)}>
                  {(shown) => (
                    <ul className="space-y-3">
                      {shown.map((r) => (
                        <li key={r.targetId}><ResultCard result={r} requestedQty={entry.quantity} /></li>
                      ))}
                    </ul>
                  )}
                </ResultFilters>
              ) : (
                <div className="border border-dashed border-neutral-300 rounded-sm py-12 text-center">
                  <p className="text-[11px] mono-track-wide text-neutral-500">DETAILED RESULTS NOT ARCHIVED FOR THIS RUN</p>
                </div>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

const MiniStat = ({ label, value, strong }) => (
  <div className={`border rounded-sm px-3 py-2.5 ${strong ? 'bg-emerald-600 text-white border-emerald-600' : 'border-neutral-300'}`}>
    <div className="text-[18px] font-extrabold mono-track-tight tabular-nums leading-none">{value}</div>
    <div className={`mt-1.5 text-[9px] mono-track-wide font-medium ${strong ? 'text-neutral-300' : 'text-neutral-500'}`}>{label}</div>
  </div>
);

export default HistoryDetail;
