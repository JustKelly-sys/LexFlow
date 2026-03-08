import { useState, useEffect } from 'react';
import { Navbar } from '@/components/lexflow/Navbar';
import { AudioUploader } from '@/components/lexflow/AudioUploader';
import { ExecutiveMetrics } from '@/components/lexflow/ExecutiveMetrics';
import { BillingLedger, BillingEntry } from '@/components/lexflow/BillingLedger';

const BILLING_RATE = 2500; // ZAR per hour

export default function App() {
  // ==========================================
  // BACKEND LOGIC & STATE (UNCHANGED)
  // ==========================================
  const [entries, setEntries] = useState<BillingEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const fetchBilling = async () => {
    try {
      const res = await fetch('/billing');
      if (res.ok) {
        const data = await res.json();
        // Map CSV entries from backend to BillingEntry shape
        const mapped: BillingEntry[] = (data.entries || []).map((e: any, i: number) => {
          // Parse duration string (e.g. "2 hours", "30 minutes") to decimal hours
          const durStr = (e.Duration || e.duration || '0').toLowerCase();
          let hours = 0;
          const hourMatch = durStr.match(/([\.\d]+)\s*h/);
          const minMatch = durStr.match(/([\.\d]+)\s*m/);
          if (hourMatch) hours += parseFloat(hourMatch[1]);
          if (minMatch) hours += parseFloat(minMatch[1]) / 60;
          if (!hourMatch && !minMatch) hours = parseFloat(durStr) || 0;

          // Parse amount string (e.g. "R5000") to number
          const amtStr = (e['Billable Amount'] || e.billable_amount || '0').replace(/[^\d.]/g, '');
          const amount = parseFloat(amtStr) || 0;

          return {
            id: String(i),
            timestamp: e.Timestamp || e.timestamp || new Date().toISOString(),
            clientName: e['Client Name'] || e.client_name || 'Unknown',
            matterDescription: e['Matter Description'] || e.matter_description || '',
            duration: hours,
            amount: amount,
          };
        });
        setEntries(mapped.reverse());
      }
    } catch (e) {
      console.error("Failed to fetch billing", e);
    }
  };

  useEffect(() => {
    fetchBilling();
    const interval = setInterval(fetchBilling, 10000);
    return () => clearInterval(interval);
  }, []);

  // Upload handler: receives a File from AudioUploader, posts via FormData
  const handleUpload = async (file: File) => {
    setIsProcessing(true);
    setStatusMsg('Transcribing with Gemini AI...');

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const res = await fetch('/transcribe', {
        method: 'POST',
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
    window.open('/billing/csv', '_blank');
  };

  const totalHours = entries.reduce((acc, curr) => acc + curr.duration, 0);
  const totalRevenue = entries.reduce((acc, curr) => acc + curr.amount, 0);

  // ==========================================
  // UI RENDER (FIREBASE DESIGN)
  // ==========================================
  return (
    <main className="relative min-h-screen pt-24 px-8 md:px-16 lg:px-24 overflow-x-hidden">
      {/* Visual Background Layers */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden bg-background">
        {/* Top Wireframe Pattern */}
        <div className="absolute inset-0 topo-pattern opacity-60" />
        {/* Subtle Gradient */}
        <div className="absolute bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-background via-background/60 to-transparent" />
      </div>

      <Navbar />

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
