import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { PortalsAPI, DistributorsAPI } from '../lib/api';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner';
import { Eye, EyeOff, Loader2, ShieldCheck, ShieldAlert } from 'lucide-react';

const PORTAL_TYPES = [
  { value: 'SUNSHOP', label: 'SUNSHOP', hint: 'Real adapter available' },
  { value: 'GENERIC', label: 'GENERIC', hint: 'Heuristic — works on many portals' },
];

/**
 * Add / Edit distributor sheet. In edit mode, existing distributor is passed via `distributor` prop.
 * On save, credentials are encrypted at backend.
 */
const AddDistributorSheet = ({ open, onOpenChange, distributor = null }) => {
  const isEdit = !!distributor;
  const { addDistributor, updateDistributor } = useApp();

  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [portal, setPortal] = useState('');
  const [portalType, setPortalType] = useState('SUNSHOP');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [portals, setPortals] = useState([]);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    if (!open) return;
    setTestResult(null);
    if (distributor) {
      setName(distributor.name || '');
      setUrl(distributor.url || '');
      setPortal(distributor.portal || '');
      setPortalType(distributor.portalType || 'SUNSHOP');
      setUsername(distributor.username || '');
      setPassword(''); // never prefill
    } else {
      setName(''); setUrl(''); setPortal(''); setPortalType('SUNSHOP');
      setUsername(''); setPassword('');
    }
    (async () => {
      try {
        const list = await PortalsAPI.list();
        const active = list.filter((p) => p.status === 'ACTIVE');
        setPortals(active);
        if (!distributor && active.length && !portal) setPortal(active[0].name);
      } catch (e) { console.error(e); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, distributor]);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !url.trim() || !portal) { toast.error('Name, URL and portal are required'); return; }
    try {
      setSaving(true);
      const payload = {
        name: name.trim().toUpperCase(),
        url: url.trim(),
        portal,
        portalType,
        username: username.trim() || null,
      };
      if (password) payload.password = password;
      if (isEdit) {
        await updateDistributor(distributor.id, payload);
        toast('Distributor updated');
      } else {
        await addDistributor(payload);
        toast('Distributor added');
      }
      onOpenChange(false);
    } catch (err) {
      console.error(err);
      toast.error('Save failed');
    } finally { setSaving(false); }
  };

  const runTestLogin = async () => {
    if (!isEdit) { toast.error('Save distributor first, then test'); return; }
    if (!distributor.hasCredentials && !password) { toast.error('Set password first'); return; }
    try {
      setTesting(true);
      setTestResult(null);
      // If new password entered but not saved, persist first
      if (password) await updateDistributor(distributor.id, { password });
      const res = await DistributorsAPI.testLogin(distributor.id);
      setTestResult(res);
      toast(res.ok ? 'Login OK' : 'Login failed');
    } catch (e) { toast.error('Test failed'); }
    finally { setTesting(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="rounded-t-lg border-neutral-950 max-h-[92vh] overflow-y-auto">
        <SheetHeader className="text-left">
          <SheetTitle className="text-[20px] font-extrabold mono-track uppercase">
            {isEdit ? 'EDIT DISTRIBUTOR' : 'ADD DISTRIBUTOR'}
          </SheetTitle>
          <p className="text-[11px] text-neutral-500 mono-track-wide font-medium">
            {isEdit ? 'UPDATE CREDENTIALS OR DETAILS' : 'REGISTER A NEW DISTRIBUTOR ENDPOINT'}
          </p>
        </SheetHeader>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <Field label="DISTRIBUTOR NAME">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. saroj pharma"
              className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[15px]" />
          </Field>

          <Field label="PORTAL URL">
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.sunshop.co.in"
              className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[13px] font-mono" />
          </Field>

          <Field label="PORTAL">
            <div className="flex flex-wrap gap-2">
              {portals.map((p) => (
                <button key={p.id} type="button" onClick={() => setPortal(p.name)}
                  className={`h-10 px-3 rounded-sm text-[11px] mono-track-wide font-semibold border press ${
                    portal === p.name ? 'bg-neutral-950 text-white border-neutral-950' : 'bg-white text-neutral-950 border-neutral-300 hover:border-neutral-950'
                  }`}>{p.name}</button>
              ))}
            </div>
          </Field>

          <Field label="ADAPTER TYPE">
            <div className="flex flex-wrap gap-2">
              {PORTAL_TYPES.map((p) => (
                <button key={p.value} type="button" onClick={() => setPortalType(p.value)}
                  className={`h-10 px-3 rounded-sm text-[11px] mono-track-wide font-semibold border press ${
                    portalType === p.value ? 'bg-neutral-950 text-white border-neutral-950' : 'bg-white text-neutral-950 border-neutral-300 hover:border-neutral-950'
                  }`} title={p.hint}>{p.label}</button>
              ))}
            </div>
          </Field>

          <div className="pt-4 mt-2 border-t border-neutral-200">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-neutral-500" strokeWidth={2} />
              <p className="text-[10px] mono-track-wide text-neutral-500">CREDENTIALS · ENCRYPTED AT REST</p>
            </div>

            <Field label="USERNAME">
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="portal login id" autoComplete="off"
                className="w-full h-12 px-4 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[14px] font-mono" />
            </Field>

            <Field label={isEdit && distributor.hasCredentials ? 'PASSWORD (LEAVE BLANK TO KEEP EXISTING)' : 'PASSWORD'}>
              <div className="relative">
                <input value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? 'text' : 'password'} placeholder="••••••••" autoComplete="new-password"
                  className="w-full h-12 px-4 pr-11 border border-neutral-300 rounded-sm focus:outline-none focus:border-neutral-950 text-[14px] font-mono" />
                <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-neutral-500 hover:text-neutral-950">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </Field>
          </div>

          {testResult && (
            <div className={`border rounded-sm px-3 py-2.5 flex items-start gap-2 text-[11px] mono-track-tight ${
              testResult.ok ? 'border-neutral-950 bg-neutral-50 text-neutral-950' : 'border-neutral-400 bg-neutral-50 text-neutral-700'
            }`}>
              {testResult.ok ? <ShieldCheck className="w-3.5 h-3.5 mt-0.5" /> : <ShieldAlert className="w-3.5 h-3.5 mt-0.5" />}
              <div>
                <div className="font-semibold">{testResult.ok ? 'LOGIN SUCCESSFUL' : 'LOGIN FAILED'}</div>
                <div className="opacity-80 mt-0.5">{testResult.detail}</div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 pt-1">
            {isEdit && (
              <button type="button" onClick={runTestLogin} disabled={testing || saving}
                className="h-14 border border-neutral-950 hover:bg-neutral-50 rounded-sm flex items-center justify-center gap-2 text-[12px] mono-track-wide font-bold press disabled:opacity-70">
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                {testing ? 'TESTING…' : 'TEST LOGIN'}
              </button>
            )}
            <button type="submit" disabled={saving}
              className={`h-14 bg-neutral-950 hover:bg-neutral-800 disabled:opacity-70 text-white rounded-sm flex items-center justify-center text-[13px] mono-track-wide font-bold press ${isEdit ? '' : 'col-span-2'}`}>
              {saving ? 'SAVING…' : (isEdit ? 'SAVE CHANGES' : 'ADD DISTRIBUTOR')}
            </button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">{label}</label>
    {children}
  </div>
);

export default AddDistributorSheet;
