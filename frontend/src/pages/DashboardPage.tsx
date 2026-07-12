import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Upload, ArrowRight, Briefcase, Loader2 } from "lucide-react";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { BillingEntry } from "@/components/lexflow/BillingLedger";
import { formatZAR } from "@/lib/formatters";
import { toast } from "sonner";
import type { Session } from "@supabase/supabase-js";
import type { PendingReview } from "@/lib/types";

interface DashboardPageProps {
  entries: BillingEntry[];
  totalHours: number;
  totalRevenue: number;
  session: Session;
  onUploadComplete: (entries: PendingReview[], confidence: number | null) => void;
}

export function DashboardPage({ entries, totalHours, totalRevenue, session, onUploadComplete }: DashboardPageProps) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const recentEntries = entries.slice(0, 5);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setUploading(true);
    toast.loading('Processing audio file...');

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const res = await fetch('/transcribe', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        body: formData,
      });
      toast.dismiss();

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Processing failed');
      } else {
        const data = await res.json();
        const extracted = data.entries || [data];
        const conf = data.confidence;
        toast.success(`Extraction complete \u2014 ${extracted.length} ${extracted.length === 1 ? 'entry' : 'entries'} found.`);
        onUploadComplete(extracted.map((en: Record<string, string>) => ({ ...en, original_ai_output: { ...en } })), conf ?? null);
        navigate('/review');
      }
    } catch {
      toast.dismiss();
      toast.error('Network error. Please check your connection.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Metrics strip */}
      <MetricsStrip items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Total Hours", value: totalHours.toFixed(1), unit: "hrs" },
        { label: "Matters Handled", value: entries.length },
        { label: "Data Quality", value: entries.length > 0 ? `${Math.round((entries.filter(e => e.clientName && e.clientName !== "Unknown" && e.matterDescription.length > 10 && e.duration > 0 && e.amount > 0).length / entries.length) * 100)}%` : "N/A", accent: true },
      ]} />

      {/* Primary CTAs — differentiated */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button onClick={() => navigate('/dictate')}
          className="bento-card p-8 flex items-center gap-6 hover:shadow-md transition-all group text-left">
          <div className="w-14 h-14 bg-primary flex items-center justify-center rounded-lg shrink-0">
            <Mic size={24} className="text-primary-foreground" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-medium text-primary" style={{ fontFamily: "'Playfair Display', serif" }}>New Dictation</h3>
            <p className="text-sm text-muted-foreground mt-1">Record a live voice note to generate billing entries</p>
          </div>
          <ArrowRight size={20} className="text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
        </button>

        <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
          className="bento-card p-8 flex items-center gap-6 hover:shadow-md transition-all group text-left">
          <div className="w-14 h-14 border border-border flex items-center justify-center rounded-lg shrink-0">
            {uploading ? <Loader2 size={24} className="text-primary animate-spin" /> : <Upload size={24} className="text-primary" />}
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-medium text-primary" style={{ fontFamily: "'Playfair Display', serif" }}>
              {uploading ? 'Processing...' : 'Upload Recording'}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {uploading ? 'Extracting billing data from your file' : 'Select an audio file (MP3, WAV, M4A, WebM)'}
            </p>
          </div>
          {!uploading && <ArrowRight size={20} className="text-muted-foreground group-hover:text-primary transition-colors shrink-0" />}
        </button>
      </div>
      <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleFileSelect} className="hidden" />

      {/* Recent Entries */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl text-primary" style={{ fontFamily: "'Playfair Display', serif" }}>Recent Entries</h2>
            <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] mt-1">Latest billing activity</p>
          </div>
          <button onClick={() => navigate('/ledger')}
            className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
            View Full Ledger <ArrowRight size={12} />
          </button>
        </div>

        <div className="bento-card divide-y divide-border">
          {recentEntries.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Briefcase size={32} className="mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm">No billing entries yet. Start a dictation to create your first entry.</p>
            </div>
          ) : (
            recentEntries.map((entry, i) => (
              <button key={entry.id || i} onClick={() => navigate(`/entry/${entry.id}`)}
                className="w-full flex items-center gap-6 px-6 py-5 hover:bg-secondary/30 transition-colors text-left">
                <div className="text-xs text-muted-foreground tabular-nums min-w-[80px]"
                  style={{ fontFeatureSettings: "'tnum' on" }}>
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-primary">{entry.clientName}</div>
                  <div className="text-xs text-muted-foreground truncate mt-0.5">{entry.matterDescription}</div>
                </div>
                <div className="text-xs text-muted-foreground tabular-nums"
                  style={{ fontFeatureSettings: "'tnum' on" }}>{entry.duration.toFixed(1)} hrs</div>
                <div className="text-sm font-medium text-primary tabular-nums min-w-[90px] text-right"
                  style={{ fontFeatureSettings: "'tnum' on" }}>{formatZAR(entry.amount)}</div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Bottom buttons REMOVED — nav handles these */}
    </div>
  );
}
