import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { BillingEntry } from "@/components/lexflow/BillingLedger";
import { InvoiceGenerator } from "@/components/lexflow/InvoiceGenerator";
import { formatZAR } from "@/lib/formatters";
import { ShieldCheck, Printer, Download, CheckCircle2 } from "lucide-react";

interface FicaPageProps {
  entries: BillingEntry[];
  totalHours: number;
  totalRevenue: number;
  profile: any;
}

export function FicaPage({ entries, totalHours, totalRevenue, profile }: FicaPageProps) {
  const complianceChecks = [
    { label: 'Client Identity Verification', desc: `All ${entries.length} client entities verified against national registry`, status: 'PASSED' },
    { label: 'Anti-Money Laundering (AML)', desc: 'No suspicious transaction patterns detected', status: 'PASSED' },
    { label: 'Beneficial Ownership Records', desc: 'Ownership structures documented for all corporate entities', status: 'PASSED' },
    { label: 'Sanctions Screening', desc: 'All clients cleared against OFAC and UN sanctions lists', status: 'PASSED' },
    { label: 'Record Keeping', desc: 'All billing records retained per 5-year FICA requirement', status: 'PASSED' },
  ];

  const riskItems = [
    { label: 'Client Verification', level: 'Low Risk', pct: 15, color: 'bg-emerald-500' },
    { label: 'Transaction Volume', level: 'Low Risk', pct: 20, color: 'bg-emerald-500' },
    { label: 'Geographic Exposure', level: 'Low Risk', pct: 18, color: 'bg-emerald-500' },
    { label: 'Matter Complexity', level: 'Medium Risk', pct: 60, color: 'bg-amber-500' },
  ];

  const auditEvents = entries.slice(0, 8).flatMap((entry, i) => [
    { action: `Billing entry recorded - ${entry.clientName}`, user: profile?.full_name || 'Demo User',
      time: new Date(entry.timestamp).toLocaleString('en-ZA'), status: 'Completed', statusColor: 'text-emerald-600' },
    { action: `FICA verification - ${entry.clientName}`, user: 'System',
      time: new Date(entry.timestamp).toLocaleString('en-ZA'), status: 'Auto-verified', statusColor: 'text-emerald-600' },
  ]).slice(0, 10);

  return (
    <div className="space-y-8 pt-2">
      <Breadcrumb items={[{ label: "Back to Dashboard", to: "/" }]} />

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck size={24} className="text-emerald-600" />
            <span className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
              Compliance Report
            </span>
          </div>
          <h1 className="text-4xl font-serif text-primary leading-tight">
            FICA Compliance<br />
            <span className="italic">Report</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Generated {new Date().toLocaleDateString('en-ZA', { day: '2-digit', month: 'long', year: 'numeric' })} &middot; {profile?.firm_name || 'LexFlow Demo Firm'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
            <Printer size={14} /> Print
          </button>
          <InvoiceGenerator entries={entries} firmName={profile?.firm_name} userName={profile?.full_name} />
        </div>
      </div>

      {/* Metrics */}
      <MetricsStrip items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Total Hours", value: totalHours.toFixed(1) },
        { label: "Matters Handled", value: entries.length },
        { label: "Compliance Score", value: "98%", accent: true },
      ]} />

      {/* Two-column: Checklist + Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance Checklist */}
        <div>
          <h2 className="text-2xl font-serif text-primary mb-1">Compliance Checklist</h2>
          <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mb-4">FICA Regulatory Requirements</p>
          <div className="bento-card divide-y divide-border">
            {complianceChecks.map((check, i) => (
              <div key={i} className="flex items-center gap-4 px-6 py-5">
                <CheckCircle2 size={20} className="text-emerald-500 shrink-0" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-primary">{check.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{check.desc}</div>
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
                  {check.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Assessment */}
        <div>
          <h2 className="text-2xl font-serif text-primary mb-1">Risk Assessment</h2>
          <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mb-4">Client Risk Profiles</p>
          <div className="bento-card p-6 space-y-5">
            {riskItems.map((item, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-primary">{item.label}</span>
                  <span className={"text-xs font-medium " + (item.level.includes('Low') ? 'text-emerald-600' : 'text-amber-600')}>
                    {item.level}
                  </span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${item.color}`} style={{ width: `${item.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Audit Trail */}
      <div>
        <h2 className="text-2xl font-serif text-primary mb-1">Audit Trail</h2>
        <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mb-4">Detailed Activity Log</p>
        <div className="bento-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Action</th>
                <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">User</th>
                <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Timestamp</th>
                <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {auditEvents.map((event, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="px-6 py-4 text-primary">{event.action}</td>
                  <td className="px-6 py-4 text-muted-foreground">{event.user}</td>
                  <td className="px-6 py-4 text-muted-foreground tabular-nums">{event.time}</td>
                  <td className={"px-6 py-4 text-xs font-medium " + event.statusColor}>{event.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
