import { formatZAR } from "@/lib/formatters";
import { Clock, Banknote, FileText } from "lucide-react";

interface ExecutiveMetricsProps {
  totalHours: number;
  totalRevenue: number;
  entryCount?: number;
}

export function ExecutiveMetrics({ totalHours, totalRevenue, entryCount }: ExecutiveMetricsProps) {
  return (
    <div className="w-full border border-primary/5 bg-card">
      <div className="flex items-center divide-x divide-primary/5">
        {/* Hours */}
        <div className="flex-1 flex items-center gap-3 px-6 py-4">
          <Clock size={16} strokeWidth={1.5} className="text-muted-foreground" />
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-headline font-medium text-primary tabular-nums">
              {totalHours.toFixed(1)}
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
              hrs billed
            </span>
          </div>
        </div>

        {/* Revenue */}
        <div className="flex-1 flex items-center gap-3 px-6 py-4">
          <Banknote size={16} strokeWidth={1.5} className="text-muted-foreground" />
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-headline font-medium text-primary tabular-nums">
              {formatZAR(totalRevenue)}
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
              revenue
            </span>
          </div>
        </div>

        {/* Entry count */}
        {entryCount != null && (
          <div className="flex-1 flex items-center gap-3 px-6 py-4">
            <FileText size={16} strokeWidth={1.5} className="text-muted-foreground" />
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-headline font-medium text-primary tabular-nums">
                {entryCount}
              </span>
              <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
                entries
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
