import { formatZAR, formatDuration } from "@/lib/formatters";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
  onExport: () => void;
}

export function BillingLedger({ entries, onExport }: BillingLedgerProps) {
  return (
    <div className="w-full space-y-12 pb-32">
      <div className="flex items-end justify-between border-b border-primary/5 pb-8">
        <div className="space-y-1">
          <h3 className="text-3xl font-headline font-light text-primary tracking-tight">Billing Ledger</h3>
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Real-time Firm Activity</p>
        </div>
        <button 
          onClick={onExport}
          className="group flex items-center gap-3 px-8 py-3 border border-primary/10 hover:border-primary/30 bg-white transition-all shadow-sm hover:shadow-md"
        >
          <Download size={18} strokeWidth={1.5} className="text-accent group-hover:-translate-y-0.5 transition-transform" />
          <span className="font-headline text-sm tracking-tight font-medium uppercase">Export FICA Report</span>
        </button>
      </div>

      <Table>
        <TableHeader>
          <TableRow className="border-none hover:bg-transparent">
            <TableHead className="uppercase text-[10px] tracking-[0.2em] font-semibold text-muted-foreground">Timestamp</TableHead>
            <TableHead className="uppercase text-[10px] tracking-[0.2em] font-semibold text-muted-foreground">Client Entity</TableHead>
            <TableHead className="uppercase text-[10px] tracking-[0.2em] font-semibold text-muted-foreground">Matter Description</TableHead>
            <TableHead className="uppercase text-[10px] tracking-[0.2em] font-semibold text-muted-foreground text-right">Duration</TableHead>
            <TableHead className="uppercase text-[10px] tracking-[0.2em] font-semibold text-muted-foreground text-right">Billable Amount</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="h-48 text-center text-muted-foreground font-light italic">
                No billing entries detected. Upload a voice note to begin.
              </TableCell>
            </TableRow>
          ) : (
            entries.map((entry) => (
              <TableRow key={entry.id} className="group border-b border-primary/[0.03] transition-colors hover:bg-primary/[0.01]">
                <TableCell className="font-light text-muted-foreground py-8">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </TableCell>
                <TableCell className="relative font-medium text-primary">
                  <div className="fluted-glass absolute inset-0 opacity-0 group-hover:opacity-10 pointer-events-none transition-opacity rounded-sm" />
                  {entry.clientName}
                </TableCell>
                <TableCell className="font-light text-primary/70 italic">{entry.matterDescription}</TableCell>
                <TableCell className="text-right font-light text-primary/70">{formatDuration(entry.duration)}</TableCell>
                <TableCell className="text-right relative">
                   <div className="fluted-glass absolute inset-y-2 right-0 w-24 opacity-0 group-hover:opacity-20 pointer-events-none transition-opacity" />
                  <span className="font-headline text-lg tracking-tight font-medium text-primary">
                    {formatZAR(entry.amount)}
                  </span>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
