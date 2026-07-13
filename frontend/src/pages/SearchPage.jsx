import React, { useMemo, useState } from 'react';
import { Zap, Check, Plus, X, Pencil, KeyRound } from 'lucide-react';
import { useApp } from '../context/AppContext';
import ExtractionModal from '../components/ExtractionModal';
import AddDistributorSheet from '../components/AddDistributorSheet';
import ProductCombobox from '../components/ProductCombobox';
import { toast } from 'sonner';

const SearchPage = () => {
  const { product, setProduct, quantity, setQuantity, distributors, toggleDistributor, removeDistributor } = useApp();
  const [running, setRunning] = useState(false);
  const [openResult, setOpenResult] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const selectedCount = useMemo(() => distributors.filter((t) => t.selected).length, [distributors]);

  const handleRun = async () => {
    if (!product.trim()) { toast.error('Enter a product name'); return; }
    if (selectedCount === 0) { toast.error('Select at least one distributor'); return; }
    const withoutCreds = distributors.filter((t) => t.selected && !t.hasCredentials);
    if (withoutCreds.length === distributors.filter((t) => t.selected).length) {
      toast.error('No selected distributor has credentials. Edit one to add username/password.');
      return;
    }
    setRunning(true); setOpenResult(true);
  };

  const openEdit = (dist) => { setEditing(dist); setSheetOpen(true); };
  const openAdd = () => { setEditing(null); setSheetOpen(true); };

  return (
    <div className="w-full">
      {/* Product + Quantity */}
      <section className="pt-3 grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">PRODUCT NAME</label>
          <ProductCombobox value={product} onChange={setProduct} placeholder="enter product name" />
        </div>
        <div>
          <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">QTY</label>
          <input value={quantity} onChange={(e) => setQuantity(e.target.value.replace(/[^0-9]/g, ''))} inputMode="numeric" placeholder="10"
            className="w-full h-14 px-4 border border-neutral-300 rounded-sm bg-white text-[16px] font-bold tabular-nums text-center focus:outline-none focus:border-emerald-600" />
        </div>
      </section>

      {/* Distributors header */}
      <section className="mt-8">
        <div className="flex items-baseline justify-between">
          <span className="text-[11px] text-neutral-500 mono-track-wide font-medium">DISTRIBUTORS</span>
          <span className="text-[11px] text-neutral-500 mono-track-wide font-medium tabular-nums">{selectedCount}/{distributors.length}</span>
        </div>

        <ul className="mt-3 space-y-2.5">
          {distributors.map((t) => (
            <li key={t.id} className="group relative border border-neutral-300 rounded-sm px-3 py-3 sm:px-4 sm:py-3.5 flex items-center gap-3 card-hover bg-white">
              <button type="button" onClick={() => toggleDistributor(t.id)} aria-pressed={t.selected}
                className={`shrink-0 w-6 h-6 rounded-[3px] border border-emerald-600 flex items-center justify-center press ${t.selected ? 'bg-emerald-600 text-white' : 'bg-white text-transparent'}`}>
                <Check className="w-4 h-4" strokeWidth={3} />
              </button>

              <div className="min-w-0 flex-1" onClick={() => openEdit(t)}>
                <div className="flex items-center gap-2">
                  <div className="text-[15px] font-extrabold mono-track-tight truncate uppercase leading-tight">{t.name}</div>
                  {!t.hasCredentials && (
                    <span className="shrink-0 text-[9px] mono-track-wide font-semibold border border-neutral-400 rounded-sm px-1.5 py-0.5 text-neutral-500">
                      NO CREDS
                    </span>
                  )}
                </div>
              </div>

              <span className="shrink-0 text-[10px] mono-track-wide font-semibold border border-emerald-600 rounded-sm px-2.5 py-1.5 text-neutral-950 bg-white">{t.portal}</span>

              <button type="button" onClick={(e) => { e.stopPropagation(); openEdit(t); }}
                className="shrink-0 w-8 h-8 rounded-sm border border-neutral-300 hover:border-emerald-600 hover:bg-emerald-600 hover:text-white text-neutral-500 flex items-center justify-center press"
                aria-label="Edit distributor">
                {t.hasCredentials ? <Pencil className="w-3.5 h-3.5" strokeWidth={2} /> : <KeyRound className="w-3.5 h-3.5" strokeWidth={2} />}
              </button>

              <button type="button" onClick={(e) => { e.stopPropagation(); removeDistributor(t.id); toast('Removed'); }}
                className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-white border border-neutral-300 text-neutral-500 hover:text-white hover:bg-emerald-600 hover:border-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                aria-label="Delete">
                <X className="w-3 h-3" strokeWidth={2.5} />
              </button>
            </li>
          ))}
        </ul>

        <button type="button" onClick={openAdd}
          className="mt-3 w-full border border-dashed border-neutral-300 hover:border-emerald-600 rounded-sm py-3 flex items-center justify-center gap-2 text-[12px] mono-track-wide text-neutral-500 hover:text-neutral-950 press">
          <Plus className="w-4 h-4" strokeWidth={2.2} /> ADD DISTRIBUTOR
        </button>
      </section>

      {/* Sticky Run Button */}
      <div className="fixed bottom-[68px] inset-x-0 px-4 sm:px-6 z-30 pointer-events-none">
        <div className="mx-auto max-w-3xl pointer-events-auto">
          <button type="button" onClick={handleRun} disabled={running}
            className="w-full h-16 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-70 text-white flex items-center justify-center gap-3 rounded-sm press shadow-[0_-8px_24px_-12px_rgba(0,0,0,0.15)]">
            <Zap className="w-5 h-5 bolt-animate fill-white" strokeWidth={2} />
            <span className="text-[15px] mono-track-wide font-bold">RUN EXTRACTION</span>
          </button>
        </div>
      </div>

      <ExtractionModal open={openResult} onOpenChange={(v) => { setOpenResult(v); if (!v) setRunning(false); }} />
      <AddDistributorSheet open={sheetOpen} onOpenChange={setSheetOpen} distributor={editing} />
    </div>
  );
};

export default SearchPage;
