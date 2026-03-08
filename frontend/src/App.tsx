import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Navbar } from '@/components/lexflow/Navbar';
import { AudioUploader } from '@/components/lexflow/AudioUploader';
import { ExecutiveMetrics } from '@/components/lexflow/ExecutiveMetrics';
import { BillingLedger, BillingEntry } from '@/components/lexflow/BillingLedger';
import { AuthPage } from '@/components/lexflow/AuthPage';
import { Toaster, toast } from 'sonner';
import type { Session } from '@supabase/supabase-js';

interface PendingReview {
  client_name: string;
  matter_description: string;
  duration: string;
  billable_amount: string;
}

// Single Toaster config — no more copy-pasting
const TOASTER_OPTS = {
  unstyled: true as const,
  classNames: {
    toast: 'flex items-start gap-3 p-4 bg-white/95 backdrop-blur-xl border border-primary/10 shadow-lg w-[360px] font-sans',
    title: 'text-sm font-medium text-primary tracking-tight',
    description: 'text-xs text-muted-foreground font-light',
    closeButton: 'text-muted-foreground hover:text-primary transition-colors',
    success: 'border-l-2 border-l-emerald-500',
    error: 'border-l-2 border-l-red-500',
    info: 'border-l-2 border-l-accent',
    loading: 'border-l-2 border-l-amber-400',
  },
};

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [entries, setEntries] = useState<BillingEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [pendingReview, setPendingReview] = useState<PendingReview | null>(null);

  // Build auth headers from an EXPLICIT session (avoids stale closure)
  const buildHeaders = useCallback((s: Session) => ({
    'Authorization': `Bearer ${s.access_token}`,
    'Content-Type': 'application/json',
  }), []);

  // Fetch profile — takes session as argument, never reads stale state
  const fetchProfile = useCallback(async (s: Session) => {
    try {
      setProfileLoading(true);
      const res = await fetch('/profile', { headers: buildHeaders(s) });
      if (res.ok) {
        setProfile(await res.json());
      } else if (res.status === 401) {
        await supabase.auth.signOut();
        setSession(null);
        setProfile(null);
      } else if (res.status === 404) {
        // Profile row not created yet (trigger delay) — show onboarding
        setProfile({ onboarded: false });
      }
    } catch (e) {
      console.error('fetchProfile error', e);
    } finally {
      setProfileLoading(false);
    }
  }, [buildHeaders]);

  // Fetch billing — takes session as argument
  const fetchBilling = useCallback(async (s: Session) => {
    try {
      const res = await fetch('/billing', { headers: buildHeaders(s) });
      if (res.ok) {
        const data = await res.json();
        const mapped: BillingEntry[] = (data.entries || []).map((e: any, i: number) => {
          const durStr = (e.duration || '0').toLowerCase();
          let hours = 0;
          const hm = durStr.match(/([\d.]+)\s*h/);
          const mm = durStr.match(/([\d.]+)\s*m/);
          if (hm) hours += parseFloat(hm[1]);
          if (mm) hours += parseFloat(mm[1]) / 60;
          if (!hm && !mm) hours = parseFloat(durStr) || 0;
          const amtStr = (e.billable_amount || '0').replace(/[^\d.]/g, '');
          return {
            id: e.id || String(i),
            timestamp: e.created_at || new Date().toISOString(),
            clientName: e.client_name || 'Unknown',
            matterDescription: e.matter_description || '',
            duration: hours,
            amount: parseFloat(amtStr) || 0,
          };
        });
        setEntries(mapped);
      }
    } catch (e) {
      console.error('fetchBilling error', e);
    }
  }, [buildHeaders]);

  // Auth state listener — single source of truth
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
    });
    return () => subscription.unsubscribe();
  }, []);

  // When session changes, fetch data with the FRESH session
  useEffect(() => {
    if (session) {
      fetchProfile(session);
      fetchBilling(session);
      const interval = setInterval(() => fetchBilling(session), 15000);
      return () => clearInterval(interval);
    } else {
      setProfile(null);
      setEntries([]);
    }
  }, [session, fetchProfile, fetchBilling]);

  // Called by AuthPage after onboarding or demo seeding
  const handleAuthRefresh = useCallback(async () => {
    const { data: { session: s } } = await supabase.auth.getSession();
    if (s) {
      await fetchProfile(s);
      await fetchBilling(s);
    }
  }, [fetchProfile, fetchBilling]);

  const handleUpload = async (file: File) => {
    if (!session) return;
    setIsProcessing(true);
    setStatusMsg('Processing your voice note...');
    toast.info('Uploading audio for extraction...');

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const res = await fetch('/transcribe', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        const msg = err.detail || 'Processing failed';
        if (msg.includes('429') || msg.includes('rate limit')) {
          toast.error('High traffic. Please try again in a moment.');
        } else {
          toast.error(msg);
        }
      } else {
        const data = await res.json();
        toast.success('Extraction complete — please review below.');
        setPendingReview(data);
      }
    } catch {
      toast.error('Network error. Please check your connection.');
    } finally {
      setIsProcessing(false);
      setStatusMsg('');
    }
  };

  const handleApproveEntry = async () => {
    if (!session || !pendingReview) return;
    toast.loading('Saving to ledger...');
    try {
      const res = await fetch('/billing', {
        method: 'POST',
        headers: buildHeaders(session),
        body: JSON.stringify(pendingReview),
      });
      toast.dismiss();
      if (res.ok) {
        toast.success('Entry saved to billing ledger.');
        setPendingReview(null);
        fetchBilling(session);
      } else {
        const err = await res.json();
        toast.error('Failed to save: ' + (err.detail || 'Unknown error'));
      }
    } catch {
      toast.dismiss();
      toast.error('Network error while saving.');
    }
  };

  const handleDiscardEntry = () => {
    setPendingReview(null);
    toast.info('Entry discarded.');
  };

  const handleExport = () => {
    if (!session) return;
    fetch('/billing/csv', { headers: buildHeaders(session) })
      .then(res => {
        if (!res.ok) throw new Error('Export failed');
        return res.blob();
      })
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'billing.csv';
        a.click();
        toast.success('CSV exported.');
      })
      .catch(() => toast.error('Failed to export CSV.'));
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
    setEntries([]);
    setPendingReview(null);
  };

  const totalHours = entries.reduce((a, c) => a + c.duration, 0);
  const totalRevenue = entries.reduce((a, c) => a + c.amount, 0);

  // --- Render ---

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <div className="text-muted-foreground font-headline text-lg tracking-tight">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return (
      <>
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <AuthPage onAuth={handleAuthRefresh} />
      </>
    );
  }

  if (profileLoading && profile === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <div className="text-muted-foreground font-headline text-lg tracking-tight">Loading profile...</div>
      </div>
    );
  }

  if (!profile?.onboarded) {
    return (
      <>
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <AuthPage onAuth={handleAuthRefresh} initialMode="onboarding" />
      </>
    );
  }

  return (
    <main className="relative min-h-screen pt-24 px-8 md:px-16 lg:px-24 overflow-x-hidden">
      <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />

      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-background">
        <div className="absolute inset-0 topo-pattern opacity-60" />
        <div className="absolute bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-background via-background/60 to-transparent" />
      </div>

      <Navbar userName={profile?.full_name} firmName={profile?.firm_name} onLogout={handleLogout} />

      <div className="max-w-7xl mx-auto space-y-24 animate-in fade-in slide-in-from-bottom-4 duration-1000 relative z-10">
        <AudioUploader onUpload={handleUpload} isProcessing={isProcessing} statusMsg={statusMsg} />

        {pendingReview && (
          <div className="max-w-3xl mx-auto fluted-glass p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-headline text-2xl font-light tracking-tight text-primary">Review Extraction</h2>
                <p className="text-muted-foreground text-sm mt-1">Verify and edit before saving to your ledger</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-xs text-muted-foreground uppercase tracking-widest">Pending Review</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Client Name</label>
                <input type="text" value={pendingReview.client_name}
                  onChange={(e) => setPendingReview({ ...pendingReview, client_name: e.target.value })}
                  className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors" />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Duration</label>
                <input type="text" value={pendingReview.duration}
                  onChange={(e) => setPendingReview({ ...pendingReview, duration: e.target.value })}
                  className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors" />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Matter Description</label>
              <textarea value={pendingReview.matter_description}
                onChange={(e) => setPendingReview({ ...pendingReview, matter_description: e.target.value })}
                rows={3}
                className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors resize-none" />
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Billable Amount (ZAR)</label>
              <input type="text" value={pendingReview.billable_amount}
                onChange={(e) => setPendingReview({ ...pendingReview, billable_amount: e.target.value })}
                className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors" />
            </div>

            <div className="flex items-center gap-4 pt-4 border-t border-primary/5">
              <button onClick={handleApproveEntry}
                className="flex-1 px-8 py-4 bg-primary text-white font-headline text-lg tracking-tight hover:bg-primary/90 transition-all">
                Approve & Save to Ledger
              </button>
              <button onClick={handleDiscardEntry}
                className="px-8 py-4 border border-primary/20 text-primary font-headline text-lg tracking-tight hover:bg-primary/5 transition-all">
                Discard
              </button>
            </div>
          </div>
        )}

        <ExecutiveMetrics totalHours={totalHours} totalRevenue={totalRevenue} />
        <BillingLedger entries={entries} onExport={handleExport} />
      </div>

      <footer className="relative z-10 py-12 flex items-center justify-between text-[10px] text-muted-foreground uppercase tracking-[0.3em] font-medium border-t border-primary/5 mt-20">
        <div>LexFlow Intelligence {new Date().getFullYear()}</div>
        <div className="flex gap-8">
          <span className="cursor-pointer hover:text-primary transition-colors">Privacy Protocol</span>
          <span className="cursor-pointer hover:text-primary transition-colors">FICA Compliance</span>
          <span className="cursor-pointer hover:text-primary transition-colors">System Health</span>
        </div>
      </footer>
    </main>
  );
}
