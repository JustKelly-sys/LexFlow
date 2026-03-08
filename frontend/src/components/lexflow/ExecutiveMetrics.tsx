import { formatZAR } from "@/lib/formatters";

interface ExecutiveMetricsProps {
  totalHours: number;
  totalRevenue: number;
}

export function ExecutiveMetrics({ totalHours, totalRevenue }: ExecutiveMetricsProps) {
  return (
    <div className="grid grid-cols-2 gap-px bg-border border border-border">
      <div className="bg-card p-12 text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground mb-4">Total Hours Billed</p>
        <h2 className="text-7xl md:text-9xl font-headline font-light tracking-tighter text-primary">
          {totalHours.toFixed(1)}
        </h2>
      </div>
      <div className="bg-card p-12 text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground mb-4">Total ZAR Revenue</p>
        <h2 className="text-7xl md:text-9xl font-headline font-light tracking-tighter text-primary">
          {formatZAR(totalRevenue)}
        </h2>
      </div>
    </div>
  );
}
