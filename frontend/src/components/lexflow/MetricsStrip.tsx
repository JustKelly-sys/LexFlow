interface MetricItem {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}

interface MetricsStripProps {
  items: MetricItem[];
  compact?: boolean;
}

export function MetricsStrip({ items, compact = false }: MetricsStripProps) {
  return (
    <div className="bento-card">
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-border">
        {items.map((item, i) => (
          <div key={i} className={compact ? "px-5 py-4 text-center" : "px-6 py-6 text-center"}>
            <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground mb-2">
              {item.label}
            </div>
            <div className={`font-medium tabular-nums ${compact ? 'text-xl' : 'text-2xl'} ${item.accent ? 'text-emerald-600' : 'text-primary'}`}
              style={{ fontFamily: "'Inter', monospace", fontFeatureSettings: "'tnum' on, 'lnum' on", letterSpacing: '-0.02em' }}>
              {item.value}
              {item.unit && <span className="text-xs font-normal text-muted-foreground ml-1">{item.unit}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
