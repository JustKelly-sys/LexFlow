import { useState, useEffect, useCallback, useRef } from 'react';
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
  original_ai_output?: Record<string, string>;  // audit trail: what the AI originally extracted
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
  const [pipelineStage, setPipelineStage] = useState<'idle' | 'uploading' | 'transcribing' | 'extracting' | 'done'>('idle');
  const [statusMsg, setStatusMsg] = useState('');
  const [pendingReviews, setPendingReviews] = useState<PendingReview[]>([]);
  const [confidence, setConfidence] = useState<number | null>(null);
  const reviewRef = useRef<HTMLDivElement>(null);

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
    setPipelineStage('uploading');
    setStatusMsg('Uploading audio...');

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      setPipelineStage('transcribing');
      setStatusMsg('Transcribing audio...');

      const res = await fetch('/transcribe', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        body: formData,
      });
      setPipelineStage('extracting');
      setStatusMsg('Extracting billing entities...');

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
        // Multi-matter: data.entries is an array, data.confidence is 0-1
        const entries = data.entries || [data];
        const confidence = data.confidence;

        // Show confidence in toast
        const pct = confidence != null ? Math.round(confidence * 100) : null;
        const confLabel = pct != null
          ? pct >= 80 ? `High confidence (${pct}%)` : `Review carefully — confidence ${pct}%`
          : '';
        toast.success(`Extraction complete — ${entries.length} ${entries.length === 1 ? 'entry' : 'entries'} found. ${confLabel}`);

        // Queue all entries for review, each tagged with its original AI output for audit
        setPendingReviews(entries.map((e: any) => ({
          ...e,
          original_ai_output: { ...e },  // snapshot before human edits
        })));
        setConfidence(confidence ?? null);
        setPipelineStage('done');
        // Auto-scroll to review form after extraction
        setTimeout(() => reviewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
      }
    } catch {
      toast.error('Network error. Please check your connection.');
    } finally {
      setIsProcessing(false);
      setStatusMsg('');
      // Reset pipeline after a beat so the "done" state is visible
      setTimeout(() => setPipelineStage('idle'), 1500);
    }
  };

  const handleApproveEntry = async (index: number) => {
    if (!session || !pendingReviews[index]) return;
    const entry = pendingReviews[index];
    toast.loading('Saving to ledger...');
    try {
      const res = await fetch('/billing', {
        method: 'POST',
        headers: buildHeaders(session),
        body: JSON.stringify(entry),
      });
      toast.dismiss();
      if (res.ok) {
        const remaining = pendingReviews.filter((_, i) => i !== index);
        setPendingReviews(remaining);
        if (remaining.length === 0) setConfidence(null);
        toast.success(`Entry saved. ${remaining.length} remaining.`);
        fetchBilling(session);
      } else {
        const err = await res.json();
        const msg = err.detail || 'Unknown error';
        // Never show raw DB errors to the user
        const safeMsg = msg.includes('PGRST') || msg.includes('schema') ? 'Unable to save entry. Please try again.' : msg;
        toast.error(safeMsg);
      }
    } catch {
      toast.dismiss();
      toast.error('Network error while saving.');
    }
  };

  const handleApproveAll = async () => {
    if (!session || pendingReviews.length === 0) return;
    toast.loading(`Saving ${pendingReviews.length} entries...`);
    let saved = 0;
    for (const entry of pendingReviews) {
      try {
        const res = await fetch('/billing', {
          method: 'POST',
          headers: buildHeaders(session),
          body: JSON.stringify(entry),
        });
        if (res.ok) saved++;
      } catch { /* continue saving others */ }
    }
    toast.dismiss();
    toast.success(`${saved} of ${pendingReviews.length} entries saved.`);
    setPendingReviews([]);
    setConfidence(null);
    fetchBilling(session);
  };

  const handleDiscardEntry = (index: number) => {
    const remaining = pendingReviews.filter((_, i) => i !== index);
    setPendingReviews(remaining);
    if (remaining.length === 0) setConfidence(null);
    toast.info('Entry discarded.');
  };

  const handleUpdateReview = (index: number, field: keyof PendingReview, value: string) => {
    setPendingReviews(prev => prev.map((e, i) =>
      i === index ? { ...e, [field]: value } : e
    ));
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
    setPendingReviews([]);
    setConfidence(null);
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

      <Navbar userName={profile?.full_name} firmName={profile?.firm_name} onLogout={handleLogout} aiStatus={pipelineStage === "idle" || pipelineStage === "done" ? "ready" : "processing"} />

      <div className="max-w-7xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-1000 relative z-10">
        <AudioUploader onUpload={handleUpload} isProcessing={isProcessing} statusMsg={statusMsg} pipelineStage={pipelineStage} />

        {/* Multi-matter HITL review cards with confidence */}
        {pendingReviews.length > 0 && (
          <div ref={reviewRef} className="max-w-3xl mx-auto space-y-6">
            {/* Header with confidence badge */}
            <div className="fluted-glass p-6 flex items-center justify-between">
              <div>
                <h2 className="font-headline text-2xl font-light tracking-tight text-primary">
                  Review Extraction{pendingReviews.length > 1 ? `s (${pendingReviews.length})` : ''}
                </h2>
                <p className="text-muted-foreground text-sm mt-1">Verify and edit before saving to your ledger</p>
              </div>
              <div className="flex items-center gap-4">
                {confidence != null && (
                  <div className={`px-3 py-1.5 text-xs font-medium uppercase tracking-widest border ${
                    confidence >= 0.8 ? 'border-emerald-300 text-emerald-700 bg-emerald-50' :
                    confidence >= 0.5 ? 'border-amber-300 text-amber-700 bg-amber-50' :
                    'border-red-300 text-red-700 bg-red-50'
                  }`}>
                    {Math.round(confidence * 100)}% Confidence
                  </div>
                )}
                {pendingReviews.length > 1 && (
                  <button onClick={handleApproveAll}
                    className="px-4 py-2 bg-primary text-white text-xs font-headline uppercase tracking-widest hover:bg-primary/90 transition-all">
                    Approve All
                  </button>
                )}
              </div>
            </div>

            {/* Individual review cards */}
            {pendingReviews.map((review, idx) => (
              <div key={idx} className="fluted-glass p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {pendingReviews.length > 1 && (
                  <div className="flex items-center gap-2 pb-2 border-b border-primary/5">
                    <span className="text-xs text-muted-foreground uppercase tracking-widest font-medium">
                      Entry {idx + 1} of {pendingReviews.length}
                    </span>
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Client Name</label>
                    <input type="text" value={review.client_name}
                      onChange={(e) => handleUpdateReview(idx, 'client_name', e.target.value)}
                      className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Duration</label>
                    <input type="text" value={review.duration}
                      onChange={(e) => handleUpdateReview(idx, 'duration', e.target.value)}
                      className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors" />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Matter Description</label>
                  <textarea value={review.matter_description}
                    onChange={(e) => handleUpdateReview(idx, 'matter_description', e.target.value)}
                    rows={3}
                    className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors resize-none scrollbar-hide max-h-32 overflow-y-auto" />
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Billable Amount (ZAR)</label>
                  <input type="text" value={review.billable_amount}
                    onChange={(e) => handleUpdateReview(idx, 'billable_amount', e.target.value)}
                    className="w-full px-5 py-4 bg-white/50 border border-primary/10 text-primary text-2xl font-headline font-medium tabular-nums focus:outline-none focus:border-primary/30 transition-colors" />
                </div>

                <div className="flex items-center gap-4 pt-4 border-t border-primary/5">
                  <button onClick={() => handleApproveEntry(idx)}
                    className="flex-1 px-8 py-4 bg-primary text-white font-headline text-lg tracking-tight hover:bg-primary/90 transition-all">
                    Approve & Save
                  </button>
                  <button onClick={() => handleDiscardEntry(idx)}
                    className="px-6 py-4 text-muted-foreground text-sm font-headline tracking-tight hover:text-destructive transition-colors">
                    Discard
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <ExecutiveMetrics totalHours={totalHours} totalRevenue={totalRevenue} entryCount={entries.length} />
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
