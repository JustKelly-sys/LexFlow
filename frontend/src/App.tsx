import { useState, useEffect } from 'react';
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

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [entries, setEntries] = useState<BillingEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [pendingReview, setPendingReview] = useState<PendingReview | null>(null);

  // Auth state listener
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => subscription.unsubscribe();
  }, []);

  // Fetch profile + billing when session changes
  useEffect(() => {
    if (session) {
      fetchProfile();
      fetchBilling();
      const interval = setInterval(fetchBilling, 15000);
      return () => clearInterval(interval);
    }
  }, [session]);

  const authHeaders = () => ({
    'Authorization': `Bearer ${session?.access_token}`,
    'Content-Type': 'application/json',
  });

  const fetchProfile = async () => {
    if (!session) return;
    try {
      const res = await fetch('/profile', { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      } else if (res.status === 401) {
        await supabase.auth.signOut();
        setSession(null);
        setProfile(null);
      }
    } catch (e) {
      console.error('Failed to fetch profile', e);
    }
  };

  const fetchBilling = async () => {
    if (!session) return;
    try {
      const res = await fetch('/billing', { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        const mapped: BillingEntry[] = (data.entries || []).map((e: any, i: number) => {
          const durStr = (e.duration || '0').toLowerCase();
          let hours = 0;
          const hourMatch = durStr.match(/([\d.]+)\s*h/);
          const minMatch = durStr.match(/([\d.]+)\s*m/);
          if (hourMatch) hours += parseFloat(hourMatch[1]);
          if (minMatch) hours += parseFloat(minMatch[1]) / 60;
          if (!hourMatch && !minMatch) hours = parseFloat(durStr) || 0;
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
      console.error('Failed to fetch billing', e);
    }
  };

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
          toast.error('AI provider is experiencing high traffic. Please try again in a moment.');
        } else {
          toast.error(msg);
        }
        setStatusMsg('');
      } else {
        const data = await res.json();
        toast.success('Extraction complete — please review below.');
        setPendingReview(data);
        setStatusMsg('');
      }
    } catch (err) {
      toast.error('Network error. Please check your connection.');
      setStatusMsg('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApproveEntry = async () => {
    if (!session || !pendingReview) return;
    toast.loading('Saving to ledger...');

    try {
      const res = await fetch('/billing', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(pendingReview),
      });
      if (res.ok) {
        toast.dismiss();
        toast.success('Entry saved to billing ledger.');
        setPendingReview(null);
        fetchBilling();
      } else {
        const err = await res.json();
        toast.dismiss();
        toast.error('Failed to save: ' + (err.detail || 'Unknown error'));
      }
    } catch (e) {
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
    const url = `/billing/csv`;
    fetch(url, { headers: authHeaders() })
      .then(res => res.blob())
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'billing.csv';
        a.click();
        toast.success('CSV exported.');
      });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
    setEntries([]);
  };

  const totalHours = entries.reduce((acc, curr) => acc + curr.duration, 0);
  const totalRevenue = entries.reduce((acc, curr) => acc + curr.amount, 0);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground font-headline text-lg tracking-tight">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return (
      <>
        <Toaster
          position="top-right"
          closeButton
          toastOptions={{
            unstyled: true,
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
          }}
        />
        <AuthPage onAuth={() => { fetchProfile(); fetchBilling(); }} />
      </>
    );
  }

  if (profile === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground font-headline text-lg tracking-tight">Loading...</div>
      </div>
    );
  }

  if (!profile.onboarded) {
    return (
      <>
        <Toaster
          position="top-right"
          closeButton
          toastOptions={{
            unstyled: true,
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
          }}
        />
        <AuthPage onAuth={() => { fetchProfile(); fetchBilling(); }} />
      </>
    );
  }

  return (
    <main className="relative min-h-screen pt-24 px-8 md:px-16 lg:px-24 overflow-x-hidden">
      <Toaster
          position="top-right"
          closeButton
          toastOptions={{
            unstyled: true,
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
          }}
        />

      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-background">
        <div className="absolute inset-0 topo-pattern opacity-60" />
        <div className="absolute bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-background via-background/60 to-transparent" />
      </div>

      <Navbar userName={profile?.full_name} firmName={profile?.firm_name} onLogout={handleLogout} />

      <div className="max-w-7xl mx-auto space-y-24 animate-in fade-in slide-in-from-bottom-4 duration-1000 relative z-10">
        <AudioUploader onUpload={handleUpload} isProcessing={isProcessing} statusMsg={statusMsg} />

        {/* HITL Review Form */}
        {pendingReview && (
          <div className="max-w-3xl mx-auto fluted-glass p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-headline text-2xl font-light tracking-tight text-primary">Review AI Extraction</h2>
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
                <input
                  type="text"
                  value={pendingReview.client_name}
                  onChange={(e) => setPendingReview({ ...pendingReview, client_name: e.target.value })}
                  className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Duration</label>
                <input
                  type="text"
                  value={pendingReview.duration}
                  onChange={(e) => setPendingReview({ ...pendingReview, duration: e.target.value })}
                  className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Matter Description</label>
              <textarea
                value={pendingReview.matter_description}
                onChange={(e) => setPendingReview({ ...pendingReview, matter_description: e.target.value })}
                rows={3}
                className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors resize-none"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground uppercase tracking-widest font-medium">Billable Amount (ZAR)</label>
              <input
                type="text"
                value={pendingReview.billable_amount}
                onChange={(e) => setPendingReview({ ...pendingReview, billable_amount: e.target.value })}
                className="w-full px-4 py-3 bg-white/50 border border-primary/10 text-primary font-light focus:outline-none focus:border-primary/30 transition-colors"
              />
            </div>

            <div className="flex items-center gap-4 pt-4 border-t border-primary/5">
              <button
                onClick={handleApproveEntry}
                className="flex-1 px-8 py-4 bg-primary text-white font-headline text-lg tracking-tight hover:bg-primary/90 transition-all"
              >
                Approve & Save to Ledger
              </button>
              <button
                onClick={handleDiscardEntry}
                className="px-8 py-4 border border-primary/20 text-primary font-headline text-lg tracking-tight hover:bg-primary/5 transition-all"
              >
                Discard
              </button>
            </div>
          </div>
        )}

        <ExecutiveMetrics totalHours={totalHours} totalRevenue={totalRevenue} />

        <BillingLedger entries={entries} onExport={handleExport} />
      </div>

      <footer className="relative z-10 py-12 flex items-center justify-between text-[10px] text-muted-foreground uppercase tracking-[0.3em] font-medium border-t border-primary/5 mt-20">
        <div>LexFlow Intelligence 2025</div>
        <div className="flex gap-8">
          <span className="cursor-pointer hover:text-primary transition-colors">Privacy Protocol</span>
          <span className="cursor-pointer hover:text-primary transition-colors">FICA Compliance</span>
          <span className="cursor-pointer hover:text-primary transition-colors">System Health</span>
        </div>
      </footer>
    </main>
  );
}
