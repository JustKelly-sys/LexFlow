import { Navigate } from "react-router-dom";
import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { Check, ChevronLeft, ChevronRight, X } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import type { PendingReview } from "@/lib/types";

interface ReviewPageProps {
  session: Session;
  pendingReviews: PendingReview[];
  confidence: number | null;
  onApprove: (index: number) => Promise<void>;
  onApproveAll: () => Promise<void>;
  onDiscard: (index: number) => void;
  onUpdate: (index: number, field: keyof PendingReview, value: string) => void;
}

export function ReviewPage({ pendingReviews, confidence, onApprove, onApproveAll, onDiscard, onUpdate }: ReviewPageProps) {
  if (pendingReviews.length === 0) {
    return <Navigate to="/" replace />;
  }

  // Multi-entry: always show index 0 (entries shift on approve/discard)
  const review = pendingReviews[0];
  const total = pendingReviews.length;
  const amountNum = parseFloat((review.billable_amount || '0').replace(/[^\d.]/g, '')) || 0;
  const durStr = (review.duration || '0').toLowerCase();
  let durHours = 0;
  const hm = durStr.match(/([\d.]+)\s*h/);
  const mm = durStr.match(/([\d.]+)\s*m/);
  if (hm) durHours += parseFloat(hm[1]);
  if (mm) durHours += parseFloat(mm[1]) / 60;
  if (!hm && !mm) durHours = parseFloat(durStr) || 0;

  return (
    <div className="space-y-6 pt-2">
      <Breadcrumb items={[
        { label: "Back to Dictation", to: "/dictate" },
        { label: "Confirm Entry" },
      ]} />

      <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl sm:text-4xl font-serif text-primary">Review Billing Entry</h1>
            {total > 1 && (
              <span className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider bg-accent/10 text-accent rounded-full">
                1 of {total}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Review and edit the details below before confirming to your billing ledger.
          </p>
        </div>
        {confidence != null && (
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Confidence</span>
            <div className="w-24 h-2 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.round(confidence * 100)}%` }} />
            </div>
            <span className="text-sm font-medium tabular-nums text-primary">{Math.round(confidence * 100)}%</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Editable form */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bento-card p-6 sm:p-8 space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Client Entity</label>
              <input type="text" value={review.client_name}
                onChange={(e) => onUpdate(0, 'client_name', e.target.value)}
                className="w-full px-4 py-3 bg-white border border-border text-sm text-primary focus:outline-none focus:border-primary/40 transition-colors rounded-lg" />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Matter Description</label>
              <textarea value={review.matter_description}
                onChange={(e) => onUpdate(0, 'matter_description', e.target.value)}
                rows={4}
                className="w-full px-4 py-3 bg-white border border-border text-sm text-primary leading-relaxed focus:outline-none focus:border-primary/40 transition-colors resize-none rounded-lg" />
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Extracted from audio transcription</span>
                <span className="tabular-nums">{review.matter_description.length} chars</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Duration</label>
                <input type="text" value={review.duration}
                  onChange={(e) => onUpdate(0, 'duration', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-border text-sm text-primary focus:outline-none focus:border-primary/40 transition-colors rounded-lg" />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Billable Amount (ZAR)</label>
                <input type="text" value={review.billable_amount}
                  onChange={(e) => onUpdate(0, 'billable_amount', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-border text-sm text-primary font-medium focus:outline-none focus:border-primary/40 transition-colors rounded-lg" />
              </div>
            </div>
          </div>
        </div>

        {/* Right: Preview + actions */}
        <div className="space-y-4">
          <div className="bento-sidebar p-6 rounded-lg space-y-5">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Entry Preview</div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Client</div>
              <div className="text-lg font-medium text-primary">{review.client_name || 'Not set'}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Duration</div>
              <div className="text-3xl font-serif font-medium tabular-nums text-primary">
                {durHours.toFixed(1)} <span className="text-base font-body text-muted-foreground">hrs</span>
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Billable Amount</div>
              <div className="text-3xl font-serif font-medium tabular-nums text-primary">
                R{amountNum.toLocaleString('en-ZA')}
              </div>
            </div>
          </div>

          {/* Real action buttons ONLY */}
          <button onClick={() => onApprove(0)}
            className="w-full flex items-center justify-center gap-2 py-4 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:bg-primary/90 transition-all">
            <Check size={16} /> Confirm & Add to Ledger
          </button>

          {total > 1 && (
            <button onClick={() => onApproveAll()}
              className="w-full flex items-center justify-center gap-2 py-3 border border-primary/30 text-sm font-medium text-primary rounded-lg hover:bg-primary/5 transition-colors">
              <Check size={14} /> Approve All ({total} entries)
            </button>
          )}

          <button onClick={() => onDiscard(0)}
            className="w-full flex items-center justify-center gap-2 py-3 text-sm text-muted-foreground hover:text-destructive transition-colors">
            <X size={14} /> Discard Entry
          </button>
        </div>
      </div>
    </div>
  );
}
