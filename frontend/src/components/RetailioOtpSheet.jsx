import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { RetailioAPI } from '../lib/api';
import { Loader2, CheckCircle2, KeyRound, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

/**
 * RETAILIO one-time OTP session manager.
 * Step 1: mobile number → server opens order.retailio.in, ticks the agree
 *   checkbox, clicks Continue, selects "I am a retailer", waits for OTP.
 * Step 2: user types OTP → server verifies, cookies + localStorage saved.
 * Cookies then persist and scraper reuses them across searches.
 */
const RetailioOtpSheet = ({ open, onOpenChange, onSaved }) => {
  const [status, setStatus] = useState(null);
  const [mobile, setMobile] = useState('9448188002');
  const [otp, setOtp] = useState('');
  const [pendingId, setPendingId] = useState(null);
  const [phase, setPhase] = useState('mobile'); // mobile | otp | done
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setPhase('mobile'); setOtp(''); setPendingId(null);
      RetailioAPI.status().then(setStatus).catch(() => setStatus({ active: false }));
    }
  }, [open]);

  const sendOtp = async () => {
    if (!/^\d{10}$/.test(mobile.trim())) { toast.error('Enter a 10-digit mobile'); return; }
    setBusy(true);
    try {
      const r = await RetailioAPI.begin(mobile.trim());
      setPendingId(r.pendingId);
      setPhase('otp');
      toast.success('OTP sent to your phone');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to send OTP');
    } finally { setBusy(false); }
  };

  const verifyOtp = async () => {
    if (!/^\d{4,8}$/.test(otp.trim())) { toast.error('Enter the OTP received'); return; }
    setBusy(true);
    try {
      await RetailioAPI.verify(pendingId, otp.trim());
      toast.success('RETAILIO session saved');
      setPhase('done');
      const s = await RetailioAPI.status();
      setStatus(s);
      onSaved && onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'OTP verification failed');
    } finally { setBusy(false); }
  };

  const clearSession = async () => {
    if (!window.confirm('Log out of RETAILIO? You will need to enter OTP again.')) return;
    setBusy(true);
    try {
      await RetailioAPI.clear();
      const s = await RetailioAPI.status();
      setStatus(s);
      toast('RETAILIO session cleared');
      setPhase('mobile'); setOtp(''); setPendingId(null);
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-emerald-600 rounded-sm p-0 gap-0" data-testid="retailio-dialog">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-neutral-200">
          <DialogTitle className="text-[18px] font-extrabold mono-track uppercase leading-none flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-emerald-600" />
            RETAILIO SESSION
          </DialogTitle>
          <p className="mt-2 text-[11px] text-neutral-500 mono-track-wide font-medium">
            OTP LOGIN FOR order.retailio.in
          </p>
        </DialogHeader>

        <div className="p-6 space-y-4">
          {/* Current session status */}
          <div className="border border-neutral-200 rounded-sm p-3">
            <div className="text-[10px] mono-track-wide text-neutral-500 font-semibold mb-1">CURRENT STATUS</div>
            {status?.active ? (
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold truncate">Logged in as +91 {status.mobile}</div>
                    <div className="text-[10px] text-neutral-500 mono-track-wide truncate">since {status.since?.slice(0,16) || 'n/a'}</div>
                  </div>
                </div>
                <button type="button" onClick={clearSession} disabled={busy}
                  className="text-[11px] mono-track-wide text-red-600 hover:text-red-700 flex items-center gap-1 shrink-0"
                  data-testid="rio-clear-btn">
                  <Trash2 className="w-3 h-3" /> LOGOUT
                </button>
              </div>
            ) : (
              <div className="text-[12px] text-neutral-600">No active session. Send OTP to log in.</div>
            )}
          </div>

          {phase === 'mobile' && (
            <div className="space-y-3">
              <div>
                <label className="text-[10px] mono-track-wide text-neutral-500 font-semibold">MOBILE NUMBER</label>
                <div className="flex items-center gap-2 mt-1">
                  <div className="h-11 px-2.5 border border-neutral-300 rounded-sm flex items-center text-[13px] font-semibold text-neutral-500">+91</div>
                  <input type="tel" value={mobile} onChange={(e) => setMobile(e.target.value.replace(/\D/g, ''))}
                    maxLength={10} placeholder="10-digit mobile"
                    className="flex-1 h-11 px-3 border border-neutral-300 rounded-sm text-[14px] font-semibold focus:border-emerald-600 outline-none"
                    data-testid="rio-mobile-input" />
                </div>
              </div>
              <button type="button" onClick={sendOtp} disabled={busy}
                className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[12px] mono-track-wide rounded-sm press flex items-center justify-center gap-2 disabled:opacity-50"
                data-testid="rio-send-otp-btn">
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                SEND OTP
              </button>
              <p className="text-[10px] text-neutral-400 mono-track-wide leading-relaxed">
                The scraper will tick "I agree" + choose "I am a retailer" for you, then wait for OTP.
              </p>
            </div>
          )}

          {phase === 'otp' && (
            <div className="space-y-3">
              <div className="text-[12px] text-neutral-600">
                OTP sent to <span className="font-bold">+91 {mobile}</span>. Please enter it below.
              </div>
              <div>
                <label className="text-[10px] mono-track-wide text-neutral-500 font-semibold">OTP</label>
                <input type="text" inputMode="numeric" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  maxLength={8} placeholder="Enter the code from SMS" autoFocus
                  className="w-full h-11 px-3 mt-1 border border-neutral-300 rounded-sm text-[16px] font-bold tracking-widest text-center focus:border-emerald-600 outline-none"
                  data-testid="rio-otp-input" />
              </div>
              <div className="flex items-center gap-2">
                <button type="button" onClick={() => { setPhase('mobile'); setOtp(''); }}
                  className="h-11 px-4 border border-neutral-300 hover:border-emerald-600 rounded-sm text-[11px] mono-track-wide font-semibold press"
                  data-testid="rio-back-btn">
                  BACK
                </button>
                <button type="button" onClick={verifyOtp} disabled={busy}
                  className="flex-1 h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[12px] mono-track-wide rounded-sm press flex items-center justify-center gap-2 disabled:opacity-50"
                  data-testid="rio-verify-otp-btn">
                  {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                  VERIFY OTP
                </button>
              </div>
            </div>
          )}

          {phase === 'done' && (
            <div className="text-center py-4">
              <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-600 mb-2" />
              <div className="text-[14px] font-bold">SESSION SAVED</div>
              <div className="text-[11px] text-neutral-500 mt-1">Scraping order.retailio.in is now enabled.</div>
              <button type="button" onClick={() => onOpenChange(false)}
                className="mt-4 h-10 px-6 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] mono-track-wide font-semibold rounded-sm press"
                data-testid="rio-done-btn">
                CLOSE
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RetailioOtpSheet;
