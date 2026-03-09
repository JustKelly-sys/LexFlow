import { useNavigate } from "react-router-dom";
import { formatZAR, formatDuration } from "@/lib/formatters";
import { Download, Trash2 } from "lucide-react";

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
  onDelete?: (id: string) => Promise<void>;
  children?: React.ReactNode;
}

export function BillingLedger({ entries, onExport, onDelete, children }: BillingLedgerProps) {
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-3xl font-serif text-primary">Billing Ledger</h2>
          <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mt-1">Real-time firm activity</p>
        </div>
        <div className="flex items-center gap-3">
          {onExport && (
            <button onClick={onExport}
              className="flex items-center gap-2 px-5 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
              <Download size={14} /> Export CSV
            </button>
          )}
          {children}
        </div>
      </div>

      <div className="bento-card overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="border-b border-border">
              <th className="px-4 sm:px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Timestamp</th>
              <th className="px-4 sm:px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Client Entity</th>
              <th className="px-4 sm:px-6 py-4 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold hidden sm:table-cell">Matter Description</th>
              <th className="px-4 sm:px-6 py-4 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Duration</th>
              <th className="px-4 sm:px-6 py-4 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Amount</th>
              {onDelete && <th className="px-2 py-4 w-10"></th>}
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-12 text-center text-muted-foreground text-sm italic">No billing entries yet.</td></tr>
            ) : entries.map((entry) => (
              <tr key={entry.id}
                className="border-b border-border/50 hover:bg-secondary/20 transition-colors group">
                <td className="px-4 sm:px-6 py-5 text-muted-foreground tabular-nums cursor-pointer"
                  onClick={() => navigate(`/entry/${entry.id}`)}>
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </td>
                <td className="px-4 sm:px-6 py-5 font-medium text-primary cursor-pointer"
                  onClick={() => navigate(`/entry/${entry.id}`)}>{entry.clientName}</td>
                <td className="px-4 sm:px-6 py-5 text-muted-foreground italic max-w-md truncate hidden sm:table-cell cursor-pointer"
                  onClick={() => navigate(`/entry/${entry.id}`)}>{entry.matterDescription}</td>
                <td className="px-4 sm:px-6 py-5 text-right tabular-nums text-muted-foreground cursor-pointer"
                  onClick={() => navigate(`/entry/${entry.id}`)}>{formatDuration(entry.duration)}</td>
                <td className="px-4 sm:px-6 py-5 text-right tabular-nums font-semibold text-primary cursor-pointer"
                  onClick={() => navigate(`/entry/${entry.id}`)}>{formatZAR(entry.amount)}</td>
                {onDelete && (
                  <td className="px-2 py-5">
                    <button onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}
                      className="p-1.5 text-muted-foreground/30 hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                      title="Delete entry">
                      <Trash2 size={14} />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
