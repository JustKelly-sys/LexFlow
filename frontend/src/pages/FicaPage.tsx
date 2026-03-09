import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { formatZAR } from "@/lib/formatters";
import { ShieldCheck, AlertTriangle, CheckCircle2, XCircle, FileText } from "lucide-react";
import type { BillingEntry } from "@/components/lexflow/BillingLedger";

interface UserProfile {
  full_name?: string;
  firm_name?: string;
}

interface FicaPageProps {
  entries: BillingEntry[];
  totalHours: number;
  totalRevenue: number;
  profile: UserProfile;
}

export function FicaPage({ entries, totalHours, totalRevenue, profile }: FicaPageProps) {
  // Derive REAL compliance metrics from actual billing data
  const uniqueClients = [...new Set(entries.map(e => e.clientName))];
  const entriesWithClient = entries.filter(e => e.clientName && e.clientName !== 'Unspecified Client' && e.clientName !== 'Unknown');
  const clientIdentificationRate = entries.length > 0 ? Math.round((entriesWithClient.length / entries.length) * 100) : 0;
  const entriesWithDescription = entries.filter(e => e.matterDescription && e.matterDescription.length > 10);
  const descriptionRate = entries.length > 0 ? Math.round((entriesWithDescription.length / entries.length) * 100) : 0;
  const entriesWithDuration = entries.filter(e => e.duration > 0);
  const durationRate = entries.length > 0 ? Math.round((entriesWithDuration.length / entries.length) * 100) : 0;
  const entriesWithAmount = entries.filter(e => e.amount > 0);
  const amountRate = entries.length > 0 ? Math.round((entriesWithAmount.length / entries.length) * 100) : 0;
  const overallScore = entries.length > 0 ? Math.round((clientIdentificationRate + descriptionRate + durationRate + amountRate) / 4) : 0;

  const checks = [
    {
      label: 'Client Identity Verification',
      desc: `${entriesWithClient.length} of ${entries.length} entries have identified clients`,
      rate: clientIdentificationRate,
      status: clientIdentificationRate >= 80 ? 'PASS' : clientIdentificationRate >= 50 ? 'WARN' : 'FAIL',
    },
    {
      label: 'Matter Description Completeness',
      desc: `${entriesWithDescription.length} of ${entries.length} entries have detailed descriptions (>10 chars)`,
      rate: descriptionRate,
      status: descriptionRate >= 80 ? 'PASS' : descriptionRate >= 50 ? 'WARN' : 'FAIL',
    },
    {
      label: 'Time Recording Accuracy',
      desc: `${entriesWithDuration.length} of ${entries.length} entries have recorded duration`,
      rate: durationRate,
      status: durationRate >= 80 ? 'PASS' : durationRate >= 50 ? 'WARN' : 'FAIL',
    },
    {
      label: 'Billing Amount Validation',
      desc: `${entriesWithAmount.length} of ${entries.length} entries have valid billing amounts`,
      rate: amountRate,
      status: amountRate >= 80 ? 'PASS' : amountRate >= 50 ? 'WARN' : 'FAIL',
    },
  ];

  const statusIcon = (status: string) => {
    if (status === 'PASS') return <CheckCircle2 size={16} className="text-emerald-600" />;
    if (status === 'WARN') return <AlertTriangle size={16} className="text-amber-500" />;
    return <XCircle size={16} className="text-red-500" />;
  };

  const statusColor = (status: string) => {
    if (status === 'PASS') return 'text-emerald-600';
    if (status === 'WARN') return 'text-amber-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-8">
      <Breadcrumb items={[{ label: "Back to Dashboard", to: "/" }, { label: "FICA Compliance" }]} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-serif text-primary">FICA Compliance Report</h1>
          <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground font-semibold mt-2">
            Billing data quality assessment
          </p>
        </div>
        <button onClick={() => window.print()}
          className="flex items-center gap-2 px-5 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
          <FileText size={14} /> Print Report
        </button>
      </div>

      <MetricsStrip compact items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Unique Clients", value: uniqueClients.length },
        { label: "Entries Audited", value: entries.length },
        { label: "Data Quality", value: `${overallScore}%`, accent: overallScore >= 80 },
      ]} />

      {/* Compliance Checks */}
      <div className="bento-card divide-y divide-border">
        <div className="px-6 py-4">
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-primary" />
            <span className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">Compliance Checklist</span>
          </div>
        </div>
        {checks.map((check, i) => (
          <div key={i} className="px-6 py-5 flex items-start gap-4">
            {statusIcon(check.status)}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-primary">{check.label}</span>
                <span className={`text-xs font-semibold uppercase tracking-wider ${statusColor(check.status)}`}>
                  {check.status === 'PASS' ? 'Passed' : check.status === 'WARN' ? 'Warning' : 'Action Required'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{check.desc}</p>
              <div className="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-500 ${
                  check.status === 'PASS' ? 'bg-emerald-500' : check.status === 'WARN' ? 'bg-amber-400' : 'bg-red-400'
                }`} style={{ width: `${check.rate}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Client Breakdown */}
      <div className="bento-card">
        <div className="px-6 py-4 border-b border-border">
          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">Client Breakdown</span>
        </div>
        {uniqueClients.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-muted-foreground italic">No billing data to analyse.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-6 py-3 text-left text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Client</th>
                <th className="px-6 py-3 text-right text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Entries</th>
                <th className="px-6 py-3 text-right text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Total Revenue</th>
              </tr>
            </thead>
            <tbody>
              {uniqueClients.map((client) => {
                const clientEntries = entries.filter(e => e.clientName === client);
                const clientRevenue = clientEntries.reduce((sum, e) => sum + e.amount, 0);
                return (
                  <tr key={client} className="border-b border-border/50">
                    <td className="px-6 py-4 font-medium text-primary">{client}</td>
                    <td className="px-6 py-4 text-right tabular-nums text-muted-foreground">{clientEntries.length}</td>
                    <td className="px-6 py-4 text-right tabular-nums font-semibold text-primary">{formatZAR(clientRevenue)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Note about FICA */}
      <div className="bento-card p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle size={16} className="text-amber-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-sm font-medium text-primary">About This Report</div>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              This report analyses billing data quality and completeness. It does not constitute
              formal FICA verification. For full FICA compliance, firms should integrate with
              registered verification services (e.g., TransUnion, Experian SA) for identity
              verification, AML screening, and beneficial ownership checks.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
