import React, { useEffect, useRef, useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { ProductsAPI } from '../lib/api';
import { toast } from 'sonner';
import { Upload, FileSpreadsheet, Trash2, Loader2, CheckCircle2 } from 'lucide-react';

const ProductMasterSheet = ({ open, onOpenChange }) => {
  const [count, setCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const inputRef = useRef(null);

  const refresh = async () => {
    try { const r = await ProductsAPI.count(); setCount(r.count || 0); }
    catch (e) { setCount(0); }
  };

  useEffect(() => { if (open) { refresh(); setLastResult(null); } }, [open]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().match(/\.(xlsx|xls|csv)$/)) {
      toast.error('Please upload .xlsx, .xls or .csv');
      return;
    }
    try {
      setUploading(true);
      const res = await ProductsAPI.upload(file);
      setLastResult(res);
      await refresh();
      toast(`Imported ${res.inserted} products`);
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Upload failed';
      toast.error(detail);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const onClear = async () => {
    if (!window.confirm('Delete all products from the master?')) return;
    try { await ProductsAPI.clear(); await refresh(); toast('Product master cleared'); }
    catch (e) { toast.error('Failed'); }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="rounded-t-lg border-emerald-600 max-h-[85vh] overflow-y-auto">
        <SheetHeader className="text-left">
          <SheetTitle className="text-[20px] font-extrabold mono-track uppercase">PRODUCT MASTER</SheetTitle>
          <p className="text-[11px] text-neutral-500 mono-track-wide font-medium">
            UPLOAD AN EXCEL / CSV WITH COLUMNS: <span className="font-mono">PRODUCT, PACK</span>
          </p>
        </SheetHeader>

        <div className="mt-5 space-y-4">
          <div className="border border-neutral-300 rounded-sm px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-sm border border-emerald-600 flex items-center justify-center text-emerald-600">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[11px] mono-track-wide text-neutral-500">CURRENT MASTER SIZE</div>
                <div className="text-[22px] font-extrabold tabular-nums leading-none">{count.toLocaleString()}</div>
              </div>
            </div>
            {count > 0 && (
              <button type="button" onClick={onClear}
                className="h-9 px-3 border border-neutral-300 hover:border-emerald-600 hover:bg-emerald-50 rounded-sm text-[11px] mono-track-wide font-semibold flex items-center gap-1.5 press">
                <Trash2 className="w-3.5 h-3.5" /> CLEAR
              </button>
            )}
          </div>

          <input ref={inputRef} type="file" accept=".xlsx,.xls,.csv" onChange={onFile} className="hidden" />
          <button type="button" onClick={() => inputRef.current?.click()} disabled={uploading}
            className="w-full h-32 border-2 border-dashed border-neutral-300 hover:border-emerald-600 hover:bg-emerald-50 rounded-sm flex flex-col items-center justify-center gap-2 press text-neutral-500 hover:text-emerald-700 disabled:opacity-70">
            {uploading ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="text-[12px] mono-track-wide font-semibold">IMPORTING… (may take up to a minute for large files)</span>
              </>
            ) : (
              <>
                <Upload className="w-6 h-6" />
                <span className="text-[13px] mono-track-wide font-bold">CLICK TO UPLOAD .XLSX / .CSV</span>
                <span className="text-[10px] mono-track-tight opacity-70">Existing master will be replaced</span>
              </>
            )}
          </button>

          {lastResult && (
            <div className="border border-emerald-600 bg-emerald-50 rounded-sm px-4 py-3">
              <div className="flex items-center gap-2 text-emerald-700 mb-1">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-[12px] mono-track-wide font-bold">IMPORT COMPLETE</span>
              </div>
              <div className="text-[11px] mono-track-tight text-neutral-700">
                <div>Inserted <b>{lastResult.inserted?.toLocaleString?.() ?? lastResult.inserted}</b> products</div>
                <div className="mt-1 text-neutral-500">Detected columns: {Object.entries(lastResult.detectedColumns || {}).filter(([_, v]) => v).map(([k, v]) => `${k}=${v}`).join(', ')}</div>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default ProductMasterSheet;
