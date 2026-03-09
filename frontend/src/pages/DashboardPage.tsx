import { useNavigate } from "react-router-dom";
import { Mic, Upload, BookOpen, ShieldCheck, FileText, Clock, DollarSign, Briefcase, ArrowRight } from "lucide-react";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { BillingEntry } from "@/components/lexflow/BillingLedger";
import { formatZAR } from "@/lib/formatters";

interface DashboardPageProps {
  entries: BillingEntry[];
  totalHours: number;
  totalRevenue: number;
  onUploadClick: () => void;
}

export function DashboardPage({ entries, totalHours, totalRevenue, onUploadClick }: DashboardPageProps) {
  const navigate = useNavigate();
  const recentEntries = entries.slice(0, 5);

  return (
    <div className="space-y-10 pt-4">
      {/* Metrics strip */}
      <MetricsStrip items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Total Hours", value: totalHours.toFixed(1), unit: "hrs" },
        { label: "Matters Handled", value: entries.length },
        { label: "Compliance Score", value: "98%", accent: true },
      ]} />

      {/* Primary CTAs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button onClick={() => navigate('/dictate')}
          className="bento-card p-8 flex items-center gap-6 hover:shadow-md transition-all group text-left">
          <div className="w-14 h-14 bg-primary flex items-center justify-center rounded-lg">
            <Mic size={24} className="text-primary-foreground" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-serif font-medium text-primary">New Dictation</h3>
            <p className="text-sm text-muted-foreground mt-1">Record a voice note to generate billing entries</p>
          </div>
          <ArrowRight size={20} className="text-muted-foreground group-hover:text-primary transition-colors" />
        </button>

        <button onClick={onUploadClick}
          className="bento-card p-8 flex items-center gap-6 hover:shadow-md transition-all group text-left">
          <div className="w-14 h-14 border border-border flex items-center justify-center rounded-lg">
            <Upload size={24} className="text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-serif font-medium text-primary">Upload Recording</h3>
            <p className="text-sm text-muted-foreground mt-1">Upload an existing audio file for processing</p>
          </div>
          <ArrowRight size={20} className="text-muted-foreground group-hover:text-primary transition-colors" />
        </button>
      </div>

      {/* Recent Entries */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-serif text-primary">Recent Entries</h2>
            <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] mt-1">Latest billing activity</p>
          </div>
          <button onClick={() => navigate('/ledger')}
            className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
            View Full Ledger <ArrowRight size={12} />
          </button>
        </div>

        <div className="bento-card divide-y divide-border">
          {recentEntries.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">
              <Briefcase size={32} className="mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm">No billing entries yet. Start a dictation to create your first entry.</p>
            </div>
          ) : (
            recentEntries.map((entry, i) => (
              <button key={entry.id || i} onClick={() => navigate('/ledger')}
                className="w-full flex items-center gap-6 px-6 py-5 hover:bg-secondary/30 transition-colors text-left">
                <div className="text-xs text-muted-foreground tabular-nums min-w-[80px]">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-primary">{entry.clientName}</div>
                  <div className="text-xs text-muted-foreground truncate mt-0.5">{entry.matterDescription}</div>
                </div>
                <div className="text-xs text-muted-foreground tabular-nums">{entry.duration.toFixed(1)} hrs</div>
                <div className="text-sm font-medium text-primary tabular-nums min-w-[90px] text-right">{formatZAR(entry.amount)}</div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-3 gap-4">
        <button onClick={() => navigate('/ledger')}
          className="bento-card p-5 flex items-center gap-3 hover:shadow-md transition-all text-left">
          <BookOpen size={18} className="text-muted-foreground" />
          <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Billing Ledger</span>
        </button>
        <button onClick={() => navigate('/fica')}
          className="bento-card p-5 flex items-center gap-3 hover:shadow-md transition-all text-left">
          <ShieldCheck size={18} className="text-muted-foreground" />
          <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">FICA Report</span>
        </button>
        <button onClick={onUploadClick}
          className="bento-card p-5 flex items-center gap-3 hover:shadow-md transition-all text-left">
          <FileText size={18} className="text-muted-foreground" />
          <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Export PDF</span>
        </button>
      </div>
    </div>
  );
}
