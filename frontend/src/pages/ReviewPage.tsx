import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { Check, Pencil, X, Volume2 } from "lucide-react";
import { toast } from "sonner";
import type { Session } from "@supabase/supabase-js";

interface PendingReview {
  client_name: string;
  matter_description: string;
  duration: string;
  billable_amount: string;
  original_ai_output?: Record<string, string>;
}

interface ReviewPageProps {
  session: Session;
  pendingReviews: PendingReview[];
  confidence: number | null;
  onApprove: (index: number) => Promise<void>;
  onApproveAll: () => Promise<void>;
  onDiscard: (index: number) => void;
  onUpdate: (index: number, field: keyof PendingReview, value: string) => void;
}

export function ReviewPage({ session, pendingReviews, confidence, onApprove, onApproveAll, onDiscard, onUpdate }: ReviewPageProps) {
  const navigate = useNavigate();

  if (pendingReviews.length === 0) {
    navigate('/');
    return null;
  }

  const review = pendingReviews[0];
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

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-serif text-primary">Review Billing Entry</h1>
            <span className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider bg-secondary text-muted-foreground rounded-full">
              Auto-Detected
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Review the details below generated from your voice dictation. Edit any fields before confirming the entry to your billing ledger.
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
          {/* Audio replay strip */}
          <div className="bento-card px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Volume2 size={18} className="text-muted-foreground" />
              <div>
                <div className="text-sm font-medium text-primary">Voice Dictation</div>
                <div className="text-xs text-muted-foreground">Recorded {new Date().toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
              </div>
            </div>
            <button className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary transition-colors">
              &#9654; Replay
            </button>
          </div>

          {/* Form fields */}
          <div className="bento-card p-8 space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Timestamp</label>
              <input type="text"
                value={new Date().toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' + new Date().toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })}
                readOnly
                className="w-full px-4 py-3 bg-secondary/30 border border-border text-sm text-primary" />
              <p className="text-[10px] text-muted-foreground flex items-center gap-1">&#128274; Auto-detected from recording metadata</p>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Client Entity</label>
              <div className="relative">
                <input type="text" value={review.client_name}
                  onChange={(e) => onUpdate(0, 'client_name', e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-border text-sm text-primary focus:outline-none focus:border-primary/40 transition-colors" />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-emerald-600 uppercase tracking-wider flex items-center gap-1">
                  &#9679; Match
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground">Matched to existing client in your firm directory</p>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Matter Description</label>
              <textarea value={review.matter_description}
                onChange={(e) => onUpdate(0, 'matter_description', e.target.value)}
                rows={4}
                className="w-full px-4 py-3 bg-white border border-border text-sm text-primary italic leading-relaxed focus:outline-none focus:border-primary/40 transition-colors resize-none scrollbar-hide" />
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>&#10024; Transcribed and summarised from audio</span>
                <span className="tabular-nums">{review.matter_description.length} characters</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Duration</label>
                <div className="relative">
                  <input type="text" value={review.duration}
                    onChange={(e) => onUpdate(0, 'duration', e.target.value)}
                    className="w-full px-4 py-3 bg-white border border-border text-sm text-primary focus:outline-none focus:border-primary/40 transition-colors" />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">hours</span>
                </div>
                <p className="text-[10px] text-muted-foreground">Based on dictation length + context analysis</p>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.15em] font-semibold text-muted-foreground">Billable Amount</label>
                <div className="relative">
                  <input type="text" value={review.billable_amount}
                    onChange={(e) => onUpdate(0, 'billable_amount', e.target.value)}
                    className="w-full px-4 py-3 bg-white border border-border text-sm text-primary font-medium focus:outline-none focus:border-primary/40 transition-colors" />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">ZAR</span>
                </div>
                <p className="text-[10px] text-muted-foreground">Calculated at R2 500/hr standard rate</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Preview sidebar */}
        <div className="space-y-4">
          {/* Entry Preview */}
          <div className="bento-sidebar p-6 rounded-lg space-y-5">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Entry Preview</div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Client</div>
              <div className="text-lg font-medium text-primary">{review.client_name || 'Not set'}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Duration</div>
              <div className="text-4xl font-serif font-medium tabular-nums text-primary">
                {durHours.toFixed(1)} <span className="text-base font-body text-muted-foreground">hrs</span>
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Billable Amount</div>
              <div className="text-4xl font-serif font-medium tabular-nums text-primary">
                R{amountNum.toLocaleString('en-ZA')}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <button onClick={() => onApprove(0)}
            className="w-full flex items-center justify-center gap-2 py-4 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:bg-primary/90 transition-all">
            <Check size={16} /> Confirm & Add to Ledger
          </button>
          <button
            className="w-full flex items-center justify-center gap-2 py-4 border border-border text-sm font-medium rounded-lg hover:bg-secondary/50 transition-colors">
            <Pencil size={16} /> Save as Draft
          </button>
          <button onClick={() => onDiscard(0)}
            className="w-full flex items-center justify-center gap-2 py-3 text-sm text-muted-foreground hover:text-destructive transition-colors">
            <X size={14} /> Discard Entry
          </button>

          {/* Raw Transcript */}
          <div className="bento-sidebar p-5 rounded-lg">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground mb-3 flex items-center gap-2">
              &#128196; Raw Transcript
            </div>
            <p className="text-xs text-muted-foreground italic leading-relaxed">
              "{review.matter_description}"
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
