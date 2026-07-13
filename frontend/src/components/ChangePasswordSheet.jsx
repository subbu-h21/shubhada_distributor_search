import React, { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import { Eye, EyeOff, KeyRound, Loader2 } from 'lucide-react';

const ChangePasswordSheet = ({ open, onOpenChange }) => {
  const { changePassword } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!current || !next) { toast.error('All fields required'); return; }
    if (next.length < 4) { toast.error('New password too short'); return; }
    if (next !== confirm) { toast.error('Confirmation does not match'); return; }
    try {
      setSaving(true);
      await changePassword(current, next);
      toast('Password updated');
      setCurrent(''); setNext(''); setConfirm('');
      onOpenChange(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Change failed');
    } finally { setSaving(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="rounded-t-lg border-emerald-600 max-h-[85vh] overflow-y-auto">
        <SheetHeader className="text-left">
          <SheetTitle className="text-[20px] font-extrabold mono-track uppercase">CHANGE PASSWORD</SheetTitle>
          <p className="text-[11px] text-neutral-500 mono-track-wide font-medium">MIN 4 CHARACTERS</p>
        </SheetHeader>

        <form onSubmit={submit} className="mt-5 space-y-4">
          {[
            ['CURRENT PASSWORD', current, setCurrent],
            ['NEW PASSWORD', next, setNext],
            ['CONFIRM NEW PASSWORD', confirm, setConfirm],
          ].map(([label, val, set]) => (
            <div key={label}>
              <label className="block text-[11px] text-neutral-500 mono-track-wide font-medium mb-2">{label}</label>
              <div className="relative">
                <input value={val} onChange={(e) => set(e.target.value)} type={show ? 'text' : 'password'} autoComplete="new-password"
                  className="w-full h-12 px-4 pr-11 border border-neutral-300 rounded-sm focus:outline-none focus:border-emerald-600 text-[15px] font-mono" />
                <button type="button" onClick={() => setShow((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-neutral-500 hover:text-neutral-900">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}

          <button type="submit" disabled={saving}
            className="w-full h-14 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-70 text-white rounded-sm flex items-center justify-center gap-2 text-[13px] mono-track-wide font-bold press">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
            {saving ? 'SAVING…' : 'UPDATE PASSWORD'}
          </button>
        </form>
      </SheetContent>
    </Sheet>
  );
};

export default ChangePasswordSheet;
