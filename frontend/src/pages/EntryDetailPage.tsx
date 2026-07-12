import { useMemo, useState } from "react";
import { useParams, useNavigate, Navigate } from "react-router-dom";
import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { formatZAR, formatDuration } from "@/lib/formatters";
import { Pencil, Trash2, ArrowLeft, Check, X } from "lucide-react";
import type { BillingEntry } from "@/components/lexflow/BillingLedger";
import { toast } from "sonner";
import type { UserProfile } from "@/lib/types";

interface EntryDetailPageProps {
  entries: BillingEntry[];
  profile: UserProfile;
  onDelete?: (id: string) => Promise<void>;
  onEdit?: (id: string, updates: Record<string, string>) => Promise<void>;
}

export function EntryDetailPage({ entries, profile, onDelete, onEdit }: EntryDetailPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);

  const entry = entries.find(e => e.id === id);

  // Editable fields
  const [editClient, setEditClient] = useState('');
  const [editMatter, setEditMatter] = useState('');
  const [editDuration, setEditDuration] = useState('');
  const [editAmount, setEditAmount] = useState('');

  // Stable reference number derived from entry ID
  const refNumber = useMemo(() => {
    if (!entry) return '';
    const hash = entry.id.split('').reduce((a, c) => ((a << 5) - a + c.charCodeAt(0)) | 0, 0);
    const num = Math.abs(hash) % 9000 + 1000;
    return `LEX-${new Date(entry.timestamp).getFullYear()}-${num}`;
  }, [entry]);

  if (!entry) return <Navigate to="/ledger" replace />;

  const startEditing = () => {
    setEditClient(entry.clientName);
    setEditMatter(entry.matterDescription);
    setEditDuration(formatDuration(entry.duration));
    setEditAmount(formatZAR(entry.amount));
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
  };

  const saveEdit = async () => {
    if (!onEdit) return;
    setSaving(true);
    try {
      await onEdit(entry.id, {
        client_name: editClient,
        matter_description: editMatter,
        duration: editDuration,
        billable_amount: editAmount,
      });
      toast.success('Entry updated.');
      setEditing(false);
    } catch {
      toast.error('Failed to update entry.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete(entry.id);
      toast.success('Entry deleted.');
      navigate('/ledger');
    } catch {
      toast.error('Failed to delete entry.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Breadcrumb items={[
        { label: "Dashboard", to: "/" },
        { label: "Ledger", to: "/ledger" },
        { label: entry.clientName },
      ]} />

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-semibold mb-1">
            Entry #{refNumber}
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif text-primary">{editing ? 'Edit Entry' : entry.clientName}</h1>
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <button onClick={cancelEditing}
                className="flex items-center gap-2 px-4 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
                <X size={14} /> Cancel
              </button>
              <button onClick={saveEdit} disabled={saving}
                className="flex items-center gap-2 px-4 py-2.5 border border-emerald-500 bg-emerald-50 text-sm font-medium text-emerald-700 hover:bg-emerald-100 transition-colors rounded-lg disabled:opacity-50">
                <Check size={14} /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </>
          ) : (
            <>
              <button onClick={startEditing}
                className="flex items-center gap-2 px-4 py-2.5 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
                <Pencil size={14} /> Edit Entry
              </button>
              <button onClick={handleDelete} disabled={deleting || !onDelete}
                className="flex items-center gap-2 px-4 py-2.5 border border-destructive/30 text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors rounded-lg disabled:opacity-50">
                <Trash2 size={14} /> {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bento-card p-6 sm:p-8 space-y-6">
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-2">Client Name</div>
              {editing ? (
                <input value={editClient} onChange={e => setEditClient(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm text-primary bg-background focus:outline-none focus:ring-1 focus:ring-primary/30" />
              ) : (
                <p className="text-sm text-primary font-medium">{entry.clientName}</p>
              )}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-2">Matter Description</div>
              {editing ? (
                <textarea value={editMatter} onChange={e => setEditMatter(e.target.value)} rows={3}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm text-primary bg-background focus:outline-none focus:ring-1 focus:ring-primary/30 resize-none" />
              ) : (
                <p className="text-sm text-primary leading-relaxed">{entry.matterDescription}</p>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Date</div>
                <div className="text-sm text-primary tabular-nums">
                  {new Date(entry.timestamp).toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Duration</div>
                {editing ? (
                  <input value={editDuration} onChange={e => setEditDuration(e.target.value)}
                    className="w-full px-2 py-1 border border-border rounded text-sm text-primary bg-background focus:outline-none focus:ring-1 focus:ring-primary/30" />
                ) : (
                  <div className="text-sm text-primary tabular-nums">{formatDuration(entry.duration)}</div>
                )}
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Hourly Rate</div>
                <div className="text-sm text-primary tabular-nums">{formatZAR(profile?.hourly_rate || 2500)}/hr</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Billable Amount</div>
                {editing ? (
                  <input value={editAmount} onChange={e => setEditAmount(e.target.value)}
                    className="w-full px-2 py-1 border border-border rounded text-sm text-primary bg-background focus:outline-none focus:ring-1 focus:ring-primary/30" />
                ) : (
                  <div className="text-xl font-semibold text-primary tabular-nums">{formatZAR(entry.amount)}</div>
                )}
              </div>
            </div>
          </div>

          {/* Fee Calculation */}
          {!editing && (
            <div className="bento-card p-6 sm:p-8">
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-4">Fee Calculation</div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Time recorded</span>
                  <span className="tabular-nums text-primary">{formatDuration(entry.duration)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hourly rate</span>
                  <span className="tabular-nums text-primary">{formatZAR(profile?.hourly_rate || 2500)}/hr</span>
                </div>
                <div className="border-t border-border pt-3 flex justify-between font-semibold">
                  <span className="text-primary">Total billable</span>
                  <span className="tabular-nums text-primary">{formatZAR(entry.amount)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="bento-sidebar p-6 rounded-lg space-y-4">
            <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold">Entry Details</div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-0.5">Reference</div>
                <div className="font-mono text-xs text-primary">{refNumber}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-0.5">Created</div>
                <div className="text-primary">{new Date(entry.timestamp).toLocaleString('en-ZA')}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-0.5">Attorney</div>
                <div className="text-primary">{profile?.full_name || 'Unknown'}</div>
              </div>
              {profile?.firm_name && (
                <div>
                  <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-0.5">Firm</div>
                  <div className="text-primary">{profile.firm_name}</div>
                </div>
              )}
              {entry.source && (
                <div>
                  <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-0.5">Source</div>
                  <div className="text-primary capitalize">{entry.source === 'whatsapp' ? 'WhatsApp' : 'Web'}</div>
                </div>
              )}
            </div>
          </div>

          <button onClick={() => navigate('/ledger')}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
            <ArrowLeft size={14} /> Back to Ledger
          </button>
        </div>
      </div>
    </div>
  );
}
