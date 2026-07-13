import React, { useMemo, useState } from 'react';
import { Zap, Check, Plus, X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import ExtractionModal from '../components/ExtractionModal';
import AddTargetSheet from '../components/AddTargetSheet';
import { toast } from 'sonner';

const SearchPage = () => {
  const { product, setProduct, targets, toggleTarget, removeTarget } = useApp();
  const [running, setRunning] = useState(false);
  const [openResult, setOpenResult] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const selectedCount = useMemo(() => targets.filter((t) => t.selected).length, [targets]);

  const handleRun = async () => {
    if (!product.trim()) {
      toast.error('Enter a product name');
      return;
    }
    if (selectedCount === 0) {
      toast.error('Select at least one target');
      return;
    }
    setRunning(true);
    setOpenResult(true);
  };

  return (
    <div className="w-full">
      {/* Product Name */}
      <section className="pt-3">
        <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">
          PRODUCT NAME
        </label>
        <input
          value={product}
          onChange={(e) => setProduct(e.target.value)}
          placeholder="enter product name"
          className="w-full h-14 px-4 border border-neutral-300 rounded-sm bg-white text-[17px] font-medium tracking-tight focus:outline-none focus:border-neutral-950 focus:ring-0 placeholder:text-neutral-400 transition-colors"
        />
      </section>

      {/* Targets header */}
      <section className="mt-8">
        <div className="flex items-baseline justify-between">
          <span className="text-[11px] text-neutral-500 mono-track-wide font-medium">TARGETS</span>
          <span className="text-[11px] text-neutral-500 mono-track-wide font-medium tabular-nums">
            {selectedCount}/{targets.length}
          </span>
        </div>

        {/* Target list */}
        <ul className="mt-3 space-y-2.5">
          {targets.map((t) => (
            <li
              key={t.id}
              className="group relative border border-neutral-300 rounded-sm px-3 py-3 sm:px-4 sm:py-3.5 flex items-center gap-3 card-hover bg-white"
            >
              {/* Checkbox */}
              <button
                type="button"
                onClick={() => toggleTarget(t.id)}
                aria-pressed={t.selected}
                aria-label={`Toggle ${t.name}`}
                className={`shrink-0 w-6 h-6 rounded-[3px] border border-neutral-950 flex items-center justify-center press ${
                  t.selected ? 'bg-neutral-950 text-white' : 'bg-white text-transparent'
                }`}
              >
                <Check className="w-4 h-4" strokeWidth={3} />
              </button>

              {/* Text */}
              <div className="min-w-0 flex-1">
                <div className="text-[15px] font-extrabold mono-track-tight truncate uppercase leading-tight">
                  {t.name}
                </div>
                <div className="mt-1 text-[12px] text-neutral-500 truncate">
                  <span className="font-mono">{t.url}</span>
                </div>
              </div>

              {/* Portal badge */}
              <span className="shrink-0 text-[10px] mono-track-wide font-semibold border border-neutral-950 rounded-sm px-2.5 py-1.5 text-neutral-950 bg-white">
                {t.portal}
              </span>

              {/* Remove button (hover) */}
              <button
                type="button"
                onClick={() => { removeTarget(t.id); toast('Target removed'); }}
                className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-white border border-neutral-300 text-neutral-500 hover:text-white hover:bg-neutral-950 hover:border-neutral-950 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                aria-label="Remove target"
              >
                <X className="w-3 h-3" strokeWidth={2.5} />
              </button>
            </li>
          ))}
        </ul>

        {/* Add target */}
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="mt-3 w-full border border-dashed border-neutral-300 hover:border-neutral-950 rounded-sm py-3 flex items-center justify-center gap-2 text-[12px] mono-track-wide text-neutral-500 hover:text-neutral-950 press"
        >
          <Plus className="w-4 h-4" strokeWidth={2.2} />
          ADD TARGET
        </button>
      </section>

      {/* Sticky Run Button */}
      <div className="fixed bottom-[68px] inset-x-0 px-4 sm:px-6 z-30 pointer-events-none">
        <div className="mx-auto max-w-3xl pointer-events-auto">
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="w-full h-16 bg-neutral-950 hover:bg-neutral-800 disabled:opacity-70 text-white flex items-center justify-center gap-3 rounded-sm press shadow-[0_-8px_24px_-12px_rgba(0,0,0,0.15)]"
          >
            <Zap className="w-5 h-5 bolt-animate fill-white" strokeWidth={2} />
            <span className="text-[15px] mono-track-wide font-bold">RUN EXTRACTION</span>
          </button>
        </div>
      </div>

      <ExtractionModal
        open={openResult}
        onOpenChange={(v) => { setOpenResult(v); if (!v) setRunning(false); }}
      />

      <AddTargetSheet open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
};

export default SearchPage;
