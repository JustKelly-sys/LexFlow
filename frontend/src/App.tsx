import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Navbar } from '@/components/lexflow/Navbar';
import { AudioUploader } from '@/components/lexflow/AudioUploader';
import { ExecutiveMetrics } from '@/components/lexflow/ExecutiveMetrics';
import { BillingLedger, BillingEntry } from '@/components/lexflow/BillingLedger';
import { AuthPage } from '@/components/lexflow/AuthPage';
import type { Session } from '@supabase/supabase-js';

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [entries, setEntries] = useState<BillingEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

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
        // Stale or invalid session - sign out
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
        setStatusMsg('Error: ' + (err.detail || 'Processing failed'));
      } else {
        const data = await res.json();
        setStatusMsg('Billed: ' + data.client_name + ' / ' + data.billable_amount);
        fetchBilling();
      }
    } catch (err) {
      setStatusMsg('Network error occurred.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExport = () => {
    if (!session) return;
    // Open CSV download with auth
    const url = `/billing/csv`;
    fetch(url, { headers: authHeaders() })
      .then(res => res.blob())
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'billing.csv';
        a.click();
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

  // Not logged in - show auth page
  if (!session) {
    return <AuthPage onAuth={() => { fetchProfile(); fetchBilling(); }} />;
  }

  // Profile not loaded yet - loading state
  if (profile === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground font-headline text-lg tracking-tight">Loading...</div>
      </div>
    );
  }

  // Profile exists but not onboarded - show onboarding
  if (!profile.onboarded) {
    return <AuthPage onAuth={() => { fetchProfile(); fetchBilling(); }} />;
  }

  return (
    <main className="relative min-h-screen pt-24 px-8 md:px-16 lg:px-24 overflow-x-hidden">
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-background">
        <div className="absolute inset-0 topo-pattern opacity-60" />
        <div className="absolute bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-background via-background/60 to-transparent" />
      </div>

      <Navbar userName={profile?.full_name} firmName={profile?.firm_name} onLogout={handleLogout} />

      <div className="max-w-7xl mx-auto space-y-24 animate-in fade-in slide-in-from-bottom-4 duration-1000 relative z-10">
        <AudioUploader onUpload={handleUpload} isProcessing={isProcessing} statusMsg={statusMsg} />

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
