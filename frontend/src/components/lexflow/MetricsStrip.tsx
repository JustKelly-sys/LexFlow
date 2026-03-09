interface MetricItem {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}

interface MetricsStripProps {
  items: MetricItem[];
}

export function MetricsStrip({ items }: MetricsStripProps) {
  return (
    <div className="bento-card">
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-border">
        {items.map((item, i) => (
          <div key={i} className="px-6 py-6 text-center">
            <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground mb-2">
              {item.label}
            </div>
            <div className={`text-3xl font-serif font-medium tabular-nums ${item.accent ? 'text-emerald-600' : 'text-primary'}`}>
              {item.value}
              {item.unit && <span className="text-base font-body font-light text-muted-foreground ml-1">{item.unit}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
