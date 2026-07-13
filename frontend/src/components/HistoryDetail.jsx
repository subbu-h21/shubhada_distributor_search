import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { CheckCircle2, XCircle, AlertOctagon } from 'lucide-react';

const STATUS_ICON = {
  IN_STOCK: CheckCircle2,
  OUT_OF_STOCK: XCircle,
  ERROR: AlertOctagon,
};

const HistoryDetail = ({ entry, onClose }) => {
  const open = !!entry;
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl border-neutral-950 rounded-sm p-0 gap-0">
        {entry && (
          <>
            <DialogHeader className="px-6 pt-6 pb-4 border-b border-neutral-200">
              <DialogTitle className="text-[20px] font-extrabold mono-track uppercase leading-none">
                {entry.product}
              </DialogTitle>
              <p className="mt-2 text-[11px] text-neutral-500 mono-track-wide font-medium">
                {new Date(entry.timestamp).toLocaleString()} · {entry.duration} · {entry.status}
              </p>
            </DialogHeader>

            <div className="px-6 py-5">
              <div className="grid grid-cols-3 gap-2 mb-5">
                <MiniStat label="TARGETS" value={entry.targetsRun} />
                <MiniStat label="FOUND" value={entry.found} strong />
                <MiniStat label="OUT" value={entry.outOfStock} />
              </div>

              {entry.results && entry.results.length > 0 ? (
                <ul className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                  {entry.results.map((r) => {
                    const Icon = STATUS_ICON[r.status] || CheckCircle2;
                    return (
                      <li key={r.targetId} className="border border-neutral-300 rounded-sm p-3 flex items-start gap-3">
                        <Icon className="w-4 h-4 mt-0.5 shrink-0" strokeWidth={2} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[13px] font-extrabold mono-track-tight uppercase truncate">{r.targetName}</span>
                            <span className="text-[9px] mono-track-wide font-semibold border border-neutral-300 rounded-sm px-1.5 py-0.5 text-neutral-500">
                              {r.portal}
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] mono-track-tight text-neutral-500">
                            {r.status === 'IN_STOCK' && (
                              <span>₹{r.price} · MRP ₹{r.mrp} · STOCK {r.stock}</span>
                            )}
                            {r.status === 'OUT_OF_STOCK' && <span>NOT AVAILABLE</span>}
                            {r.status === 'ERROR' && <span>PORTAL TIMEOUT</span>}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
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
  <div className={`border rounded-sm px-3 py-2.5 ${strong ? 'bg-neutral-950 text-white border-neutral-950' : 'border-neutral-300'}`}>
    <div className="text-[18px] font-extrabold mono-track-tight tabular-nums leading-none">{value}</div>
    <div className={`mt-1.5 text-[9px] mono-track-wide font-medium ${strong ? 'text-neutral-300' : 'text-neutral-500'}`}>{label}</div>
  </div>
);

export default HistoryDetail;
