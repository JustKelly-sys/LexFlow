import { useNavigate } from "react-router-dom";
import { formatZAR, formatDuration } from "@/lib/formatters";
import { Download } from "lucide-react";

export interface BillingEntry {
  id: string;
  timestamp: string;
  clientName: string;
  matterDescription: string;
  duration: number;
  amount: number;
}

interface BillingLedgerProps {
  entries: BillingEntry[];
  onExport?: () => void;
  children?: React.ReactNode;
}

export function BillingLedger({ entries, onExport, children }: BillingLedgerProps) {
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-serif text-primary">Billing Ledger</h2>
          <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mt-1">Real-time firm activity</p>
        </div>
        {onExport && (
          <button onClick={onExport}
            className="flex items-center gap-2 px-5 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
            <Download size={14} /> Export FICA Report
          </button>
        )}
        {children}
      </div>

      <div className="bento-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Timestamp</th>
              <th className="px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Client Entity</th>
              <th className="px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Matter Description</th>
              <th className="px-6 py-4 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Duration</th>
              <th className="px-6 py-4 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Billable Amount</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}
                onClick={() => navigate(`/entry/${entry.id}`)}
                className="border-b border-border/50 hover:bg-secondary/20 transition-colors cursor-pointer">
                <td className="px-6 py-5 text-muted-foreground tabular-nums">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </td>
                <td className="px-6 py-5 font-medium text-primary">{entry.clientName}</td>
                <td className="px-6 py-5 text-muted-foreground italic max-w-md truncate">{entry.matterDescription}</td>
                <td className="px-6 py-5 text-right tabular-nums text-muted-foreground">{formatDuration(entry.duration)}</td>
                <td className="px-6 py-5 text-right tabular-nums font-semibold text-primary">{formatZAR(entry.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
