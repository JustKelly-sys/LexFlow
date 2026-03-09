import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { BillingLedger, type BillingEntry } from "@/components/lexflow/BillingLedger";
import { InvoiceGenerator } from "@/components/lexflow/InvoiceGenerator";
import { formatZAR } from "@/lib/formatters";

interface UserProfile {
  full_name?: string;
  firm_name?: string;
  hourly_rate?: number;
  onboarded?: boolean;
}

interface LedgerPageProps {
  entries: BillingEntry[];
  totalHours: number;
  totalRevenue: number;
  onExport: () => void;
  onDelete: (id: string) => Promise<void>;
  profile: UserProfile;
}

export function LedgerPage({ entries, totalHours, totalRevenue, onExport, onDelete, profile }: LedgerPageProps) {
  return (
    <div className="space-y-8">
      <Breadcrumb items={[{ label: "Back to Dashboard", to: "/" }]} />
      <MetricsStrip compact items={[
        { label: "Total Billable", value: formatZAR(totalRevenue) },
        { label: "Total Hours", value: totalHours.toFixed(1), unit: "hrs" },
        { label: "Matters Handled", value: entries.length },
        { label: "Avg. per Entry", value: entries.length > 0 ? formatZAR(totalRevenue / entries.length) : "R0" },
      ]} />
      <BillingLedger entries={entries} onExport={onExport} onDelete={onDelete}>
        <InvoiceGenerator entries={entries} firmName={profile?.firm_name} userName={profile?.full_name} />
      </BillingLedger>
    </div>
  );
}
