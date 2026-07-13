import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { PortalsAPI } from '../lib/api';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner';

const AddTargetSheet = ({ open, onOpenChange }) => {
  const { addTarget } = useApp();
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [portal, setPortal] = useState('');
  const [portals, setPortals] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const list = await PortalsAPI.list();
        const active = list.filter((p) => p.status === 'ACTIVE');
        setPortals(active);
        if (active.length && !portal) setPortal(active[0].name);
      } catch (e) { console.error(e); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !url.trim() || !portal) {
      toast.error('Fill all fields');
      return;
    }
    try {
      setSaving(true);
      await addTarget({ name: name.trim().toUpperCase(), url: url.trim(), portal });
      toast('Target added');
      setName(''); setUrl('');
      onOpenChange(false);
    } catch (err) {
      toast.error('Failed to add target');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="rounded-t-lg border-neutral-950 max-h-[85vh]">
        <SheetHeader className="text-left">
          <SheetTitle className="text-[20px] font-extrabold mono-track uppercase">
            ADD TARGET
          </SheetTitle>
          <p className="text-[11px] text-neutral-500 mono-track-wide font-medium">
            REGISTER A NEW DISTRIBUTOR ENDPOINT
          </p>
        </SheetHeader>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <div>
            <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">
              DISTRIBUTOR NAME
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. saroj pharma"
              className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[15px]"
            />
          </div>
          <div>
            <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">
              TARGET URL
            </label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[13px] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">
              PORTAL
            </label>
            <div className="flex flex-wrap gap-2">
              {portals.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPortal(p.name)}
                  className={`h-10 px-3 rounded-sm text-[11px] mono-track-wide font-semibold border press ${
                    portal === p.name
                      ? 'bg-neutral-950 text-white border-neutral-950'
                      : 'bg-white text-neutral-950 border-neutral-300 hover:border-neutral-950'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full h-14 bg-neutral-950 hover:bg-neutral-800 disabled:opacity-70 text-white rounded-sm flex items-center justify-center text-[13px] mono-track-wide font-bold press"
          >
            {saving ? 'ADDING…' : 'ADD TARGET'}
          </button>
        </form>
      </SheetContent>
    </Sheet>
  );
};

export default AddTargetSheet;
