import { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { Navbar } from '@/components/lexflow/Navbar';
import { BillingEntry } from '@/components/lexflow/BillingLedger';
import { AuthPage } from '@/components/lexflow/AuthPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { DictationPage } from '@/pages/DictationPage';
import { ReviewPage } from '@/pages/ReviewPage';
import { EntryDetailPage } from '@/pages/EntryDetailPage';
import { FicaPage } from '@/pages/FicaPage';
import { BillingLedger } from '@/components/lexflow/BillingLedger';
import { MetricsStrip } from '@/components/lexflow/MetricsStrip';
import { InvoiceGenerator } from '@/components/lexflow/InvoiceGenerator';
import { formatZAR } from '@/lib/formatters';
import { Toaster, toast } from 'sonner';
import type { Session } from '@supabase/supabase-js';

interface PendingReview {
  client_name: string;
  matter_description: string;
  duration: string;
  billable_amount: string;
  original_ai_output?: Record<string, string>;
}

const TOASTER_OPTS = {
  unstyled: true as const,
  classNames: {
    toast: 'flex items-start gap-3 p-4 bg-white/95 backdrop-blur-xl border border-border shadow-lg w-[360px] font-body rounded-lg',
    title: 'text-sm font-medium text-primary tracking-tight',
    description: 'text-xs text-muted-foreground font-light',
    closeButton: 'text-muted-foreground hover:text-primary transition-colors',
    success: 'border-l-2 border-l-emerald-500',
    error: 'border-l-2 border-l-red-500',
    info: 'border-l-2 border-l-accent',
    loading: 'border-l-2 border-l-amber-400',
  },
};

// ── Ledger Page (inline — just wraps existing components) ──────────

function LedgerPage({ entries, totalHours, totalRevenue, onExport, profile }: any) {
  return (
    <div className="space-y-8 pt-4">
      <MetricsStrip items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Total Hours", value: totalHours.toFixed(1), unit: "hrs" },
        { label: "Matters Handled", value: entries.length },
        { label: "Compliance Score", value: "98%", accent: true },
      ]} />
      <BillingLedger entries={entries} onExport={onExport} />
      <div className="flex justify-end pb-12">
        <InvoiceGenerator entries={entries} firmName={profile?.firm_name} userName={profile?.full_name} />
      </div>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [entries, setEntries] = useState<BillingEntry[]>([]);
  const [pipelineStage, setPipelineStage] = useState<'idle' | 'uploading' | 'transcribing' | 'extracting' | 'done'>('idle');
  const [pendingReviews, setPendingReviews] = useState<PendingReview[]>([]);
  const [confidence, setConfidence] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const buildHeaders = useCallback((s: Session) => ({
    'Authorization': `Bearer ${s.access_token}`,
    'Content-Type': 'application/json',
  }), []);

  const fetchProfile = useCallback(async (s: Session) => {
    try {
      setProfileLoading(true);
      const res = await fetch('/profile', { headers: buildHeaders(s) });
      if (res.ok) setProfile(await res.json());
      else if (res.status === 401) { await supabase.auth.signOut(); setSession(null); setProfile(null); }
      else if (res.status === 404) setProfile({ onboarded: false });
    } catch (e) { console.error('fetchProfile error', e); }
    finally { setProfileLoading(false); }
  }, [buildHeaders]);

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
    } catch (e) { console.error('fetchBilling error', e); }
  }, [buildHeaders]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => { setSession(s); setLoading(false); });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (session) {
      fetchProfile(session);
      fetchBilling(session);
      const interval = setInterval(() => fetchBilling(session), 15000);
      return () => clearInterval(interval);
    } else { setProfile(null); setEntries([]); }
  }, [session, fetchProfile, fetchBilling]);

  const handleAuthRefresh = useCallback(async () => {
    const { data: { session: s } } = await supabase.auth.getSession();
    if (s) { await fetchProfile(s); await fetchBilling(s); }
  }, [fetchProfile, fetchBilling]);

  const handleEntryExtracted = useCallback((extractedEntries: any[], conf: number | null) => {
    setPendingReviews(extractedEntries);
    setConfidence(conf);
  }, []);

  const handleApproveEntry = async (index: number) => {
    if (!session || !pendingReviews[index]) return;
    const entry = pendingReviews[index];
    toast.loading('Saving to ledger...');
    try {
      const res = await fetch('/billing', { method: 'POST', headers: buildHeaders(session), body: JSON.stringify(entry) });
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
        const safeMsg = msg.includes('PGRST') || msg.includes('schema') ? 'Unable to save entry. Please try again.' : msg;
        toast.error(safeMsg);
      }
    } catch { toast.dismiss(); toast.error('Network error while saving.'); }
  };

  const handleApproveAll = async () => {
    if (!session || pendingReviews.length === 0) return;
    toast.loading(`Saving ${pendingReviews.length} entries...`);
    let saved = 0;
    for (const entry of pendingReviews) {
      try { const res = await fetch('/billing', { method: 'POST', headers: buildHeaders(session), body: JSON.stringify(entry) }); if (res.ok) saved++; } catch {}
    }
    toast.dismiss();
    toast.success(`${saved} of ${pendingReviews.length} entries saved.`);
    setPendingReviews([]); setConfidence(null); fetchBilling(session);
  };

  const handleDiscardEntry = (index: number) => {
    const remaining = pendingReviews.filter((_, i) => i !== index);
    setPendingReviews(remaining);
    if (remaining.length === 0) setConfidence(null);
    toast.info('Entry discarded.');
  };

  const handleUpdateReview = (index: number, field: keyof PendingReview, value: string) => {
    setPendingReviews(prev => prev.map((e, i) => i === index ? { ...e, [field]: value } : e));
  };

  const handleExport = () => {
    if (!session) return;
    fetch('/billing/csv', { headers: buildHeaders(session) })
      .then(res => { if (!res.ok) throw new Error('Export failed'); return res.blob(); })
      .then(blob => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'billing.csv'; a.click(); toast.success('CSV exported.'); })
      .catch(() => toast.error('Failed to export CSV.'));
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null); setProfile(null); setEntries([]); setPendingReviews([]); setConfidence(null);
  };

  const handleUploadFromDashboard = () => {
    // Navigate to dictation page where upload is available
    window.location.href = '/dictate';
  };

  const totalHours = entries.reduce((a, c) => a + c.duration, 0);
  const totalRevenue = entries.reduce((a, c) => a + c.amount, 0);

  // ── Auth gates ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <div className="text-muted-foreground text-lg tracking-tight">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return (<><Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} /><AuthPage onAuth={handleAuthRefresh} /></>);
  }

  if (profileLoading && profile === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />
        <div className="text-muted-foreground text-lg tracking-tight">Loading profile...</div>
      </div>
    );
  }

  if (!profile?.onboarded) {
    return (<><Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} /><AuthPage onAuth={handleAuthRefresh} initialMode="onboarding" /></>);
  }

  // ── Authenticated shell ─────────────────────────────────────────

  return (
    <main className="relative min-h-screen pt-20 px-8 md:px-16 lg:px-24 overflow-x-hidden bg-background">
      <Toaster position="top-right" closeButton toastOptions={TOASTER_OPTS} />

      <Navbar
        userName={profile?.full_name}
        firmName={profile?.firm_name}
        onLogout={handleLogout}
        aiStatus={pipelineStage === 'idle' || pipelineStage === 'done' ? 'ready' : 'processing'}
      />

      <div className="max-w-7xl mx-auto relative z-10 pb-12">
        <Routes>
          <Route path="/" element={
            <DashboardPage entries={entries} totalHours={totalHours} totalRevenue={totalRevenue} onUploadClick={handleUploadFromDashboard} />
          } />
          <Route path="/dictate" element={
            <DictationPage session={session} onEntryExtracted={handleEntryExtracted} />
          } />
          <Route path="/review" element={
            <ReviewPage session={session} pendingReviews={pendingReviews} confidence={confidence}
              onApprove={handleApproveEntry} onApproveAll={handleApproveAll}
              onDiscard={handleDiscardEntry} onUpdate={handleUpdateReview} />
          } />
          <Route path="/entry/:id" element={<EntryDetailPage entries={entries} profile={profile} />} />
          <Route path="/ledger" element={<LedgerPage entries={entries} totalHours={totalHours} totalRevenue={totalRevenue} onExport={handleExport} profile={profile} />} />
          <Route path="/fica" element={<FicaPage entries={entries} totalHours={totalHours} totalRevenue={totalRevenue} profile={profile} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>

      <footer className="relative z-10 py-8 flex items-center justify-between text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-medium border-t border-border max-w-7xl mx-auto">
        <div>LEXFLOW &middot; Voice-powered legal billing intelligence</div>
        <div className="flex gap-8">
          <span className="cursor-pointer hover:text-primary transition-colors">Privacy</span>
          <span className="cursor-pointer hover:text-primary transition-colors">Terms</span>
          <span className="cursor-pointer hover:text-primary transition-colors">Support</span>
        </div>
      </footer>
    </main>
  );
}
