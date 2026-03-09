import { useParams, useNavigate } from "react-router-dom";
import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { MetricsStrip } from "@/components/lexflow/MetricsStrip";
import { BillingEntry } from "@/components/lexflow/BillingLedger";
import { InvoiceGenerator } from "@/components/lexflow/InvoiceGenerator";
import { formatZAR } from "@/lib/formatters";
import { Pencil, Trash2, Download, Calendar, Building2, User, Clock } from "lucide-react";

interface EntryDetailPageProps {
  entries: BillingEntry[];
  profile: any;
}

export function EntryDetailPage({ entries, profile }: EntryDetailPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const entry = entries.find(e => e.id === id);

  if (!entry) {
    return (
      <div className="pt-8 text-center space-y-4">
        <h2 className="text-2xl font-serif text-primary">Entry not found</h2>
        <button onClick={() => navigate('/ledger')} className="text-sm text-muted-foreground hover:text-primary">
          Back to Ledger
        </button>
      </div>
    );
  }

  const hourlyRate = entry.duration > 0 ? entry.amount / entry.duration : 2500;
  const vat = entry.amount * 0.15;
  const total = entry.amount + vat;
  const relatedEntries = entries.filter(e => e.clientName === entry.clientName && e.id !== entry.id).slice(0, 5);

  return (
    <div className="space-y-8 pt-2">
      <Breadcrumb items={[
        { label: "Back to Ledger", to: "/ledger" },
        { label: "Billing Entry" },
        { label: entry.clientName },
      ]} />

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Confirmed
            </span>
            <span className="text-xs text-muted-foreground tabular-nums">
              ENTRY #LEX-{new Date(entry.timestamp).getFullYear()}-{String(Math.floor(Math.random() * 9000 + 1000))}
            </span>
          </div>
          <h1 className="text-4xl font-serif text-primary">{entry.clientName}</h1>
          <p className="text-sm text-muted-foreground mt-1">{entry.matterDescription?.slice(0, 60)}...</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
            <Pencil size={14} /> Edit Entry
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
            <Trash2 size={14} /> Delete
          </button>
          <InvoiceGenerator entries={[entry]} firmName={profile?.firm_name} userName={profile?.full_name} />
        </div>
      </div>

      {/* Metrics strip */}
      <MetricsStrip items={[
        { label: "Duration", value: entry.duration.toFixed(1), unit: "hrs" },
        { label: "Hourly Rate", value: formatZAR(hourlyRate), unit: "/hr" },
        { label: "Billable Amount", value: formatZAR(entry.amount) },
        { label: "Incl. VAT (15%)", value: formatZAR(total) },
      ]} />

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Matter Description */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h2 className="text-2xl font-serif text-primary">Matter Description</h2>
            <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold mt-1">Auto-generated from voice dictation</p>
          </div>
          <div className="bento-card p-8">
            <p className="text-sm leading-relaxed text-primary">{entry.matterDescription}</p>
            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-sm italic text-muted-foreground leading-relaxed">
                Additional notes: Follow-up meeting scheduled for review of final documentation and compliance verification.
              </p>
            </div>
          </div>

          {/* Source & Compliance */}
          <div>
            <h2 className="text-2xl font-serif text-primary">Source & Compliance</h2>
          </div>
          <div className="bento-card p-8">
            <div className="grid grid-cols-3 gap-6">
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Input Source</div>
                <div className="text-sm text-primary flex items-center gap-1.5">&#127908; Voice Dictation</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Recording Duration</div>
                <div className="text-sm text-primary">{Math.round(entry.duration * 60)} min {Math.round((entry.duration * 60 % 1) * 60)} sec</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Transcription Confidence</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: '96%' }} />
                  </div>
                  <span className="text-xs font-medium tabular-nums text-emerald-600">96%</span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-6 mt-6 pt-6 border-t border-border">
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">FICA Status</div>
                <div className="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Verified
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Matter Type</div>
                <div className="text-sm text-primary">Commercial / Technology</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Practice Area</div>
                <div className="text-sm text-primary">Corporate & Commercial Law</div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-6 mt-6 pt-6 border-t border-border">
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Responsible Attorney</div>
                <div className="text-sm text-primary">{profile?.full_name || 'Demo User'}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Firm</div>
                <div className="text-sm text-primary">{profile?.firm_name || 'LexFlow Demo Firm'}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Reference</div>
                <div className="text-sm text-primary tabular-nums">LXF/TR/{new Date(entry.timestamp).getFullYear()}/{String(Math.floor(Math.random() * 9000 + 1000))}</div>
              </div>
            </div>
          </div>

          {/* Related entries */}
          {relatedEntries.length > 0 && (
            <>
              <div className="text-center pt-6">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Other Entries for {entry.clientName}
                </span>
              </div>
              <div className="bento-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Date</th>
                      <th className="px-6 py-3 text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Description</th>
                      <th className="px-6 py-3 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Duration</th>
                      <th className="px-6 py-3 text-right text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {relatedEntries.map((e, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-secondary/20 transition-colors cursor-pointer"
                        onClick={() => navigate(`/entry/${e.id}`)}>
                        <td className="px-6 py-4 text-muted-foreground tabular-nums">
                          {new Date(e.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </td>
                        <td className="px-6 py-4 text-primary max-w-md truncate">{e.matterDescription}</td>
                        <td className="px-6 py-4 text-right tabular-nums text-muted-foreground">{e.duration.toFixed(1)} hrs</td>
                        <td className="px-6 py-4 text-right tabular-nums font-medium text-primary">{formatZAR(e.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          {/* Entry Metadata */}
          <div className="bento-sidebar p-6 rounded-lg space-y-5">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Entry Metadata</div>
            <div className="flex items-start gap-3">
              <Calendar size={16} className="text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-0.5">Timestamp</div>
                <div className="text-sm font-medium text-primary">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'long', year: 'numeric' })}
                </div>
                <div className="text-xs text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })} SAST
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Building2 size={16} className="text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-0.5">Client Entity</div>
                <div className="text-sm font-medium text-primary underline">{entry.clientName}</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <User size={16} className="text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-0.5">Created By</div>
                <div className="text-sm font-medium text-primary">{profile?.full_name || 'Demo User'}</div>
                <div className="text-xs text-muted-foreground">Voice-assisted transcription</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Clock size={16} className="text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-0.5">Last Modified</div>
                <div className="text-sm font-medium text-primary">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </div>
              </div>
            </div>
          </div>

          {/* Fee Calculation */}
          <div className="bento-sidebar p-6 rounded-lg space-y-3">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Fee Calculation</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Duration</span>
                <span className="tabular-nums">{entry.duration.toFixed(1)} hrs</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Hourly rate</span>
                <span className="tabular-nums">{formatZAR(hourlyRate)}</span>
              </div>
              <div className="flex justify-between text-sm pt-2 border-t border-border">
                <span className="text-emerald-600 font-medium">Subtotal</span>
                <span className="tabular-nums text-emerald-600 font-medium">{formatZAR(entry.amount)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">VAT (15%)</span>
                <span className="tabular-nums">{formatZAR(vat)}</span>
              </div>
              <div className="flex justify-between text-base font-medium pt-2 border-t border-border">
                <span>Total</span>
                <span className="tabular-nums">{formatZAR(total)}</span>
              </div>
            </div>
          </div>

          {/* Audit Trail */}
          <div className="bento-sidebar p-6 rounded-lg space-y-4">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Audit Trail</div>
            <div className="space-y-4">
              {[
                { label: 'Entry confirmed', time: '09:22 AM', color: 'bg-emerald-500' },
                { label: 'FICA verified', time: '09:18 AM', color: 'bg-emerald-500' },
                { label: 'Transcription complete', time: '09:16 AM', color: 'bg-amber-500' },
                { label: 'Voice dictation started', time: '09:14 AM', color: 'bg-primary/30' },
              ].map((event, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${event.color}`} />
                  <div>
                    <div className="text-sm font-medium text-primary">{event.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })} - {event.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
