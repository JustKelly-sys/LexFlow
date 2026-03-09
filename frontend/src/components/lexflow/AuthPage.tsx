import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { Loader2, ArrowRight, Mail, Lock, User, Building2 } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

type Mode = "login" | "signup" | "onboarding";

interface AuthPageProps {
  onAuth: () => void;                  // called after onboarding/demo to trigger data refresh
  initialMode?: Mode;                  // App.tsx passes "onboarding" when profile exists but !onboarded
}

// ── Constants ──────────────────────────────────────────────────────

// Demo-only credentials — this is a portfolio demo account with no real data.
// The password is intentionally client-visible to enable one-click demo access.
const DEMO_EMAIL = "demo@lexflow.app";
const DEMO_PASSWORD = "DemoLexFlow2026!";
const DEFAULT_RATE = "2500";

// ── Shared CSS ─────────────────────────────────────────────────────

const INPUT_CLASS =
  "w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors";
const LABEL_CLASS =
  "text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold";
const SUBMIT_CLASS =
  "w-full py-3 bg-primary text-primary-foreground font-headline text-sm tracking-tight hover:bg-primary/90 transition-all flex items-center justify-center gap-2";

// ====================================================================
// COMPONENT
// ====================================================================

export function AuthPage({ onAuth, initialMode = "login" }: AuthPageProps) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Onboarding-specific fields
  const [fullName, setFullName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [hourlyRate, setHourlyRate] = useState(DEFAULT_RATE);

  // ── Handlers (one per auth action, ordered by user journey) ──────

  /** Sign in with email/password. On success, onAuthStateChange in
   *  App.tsx detects the new session — we do NOT call onAuth() here
   *  to avoid a race condition with stale state. */
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });

    if (authError) {
      setError(
        authError.message.includes("Invalid login")
          ? "Invalid email or password. If you're new, click 'Create one' below."
          : authError.message
      );
      setLoading(false);
    }
    // Success: onAuthStateChange fires -> App.tsx picks up the session
  };

  /** Create a new account, auto sign-in, then show onboarding form. */
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { data, error: signUpErr } = await supabase.auth.signUp({ email, password });

    if (signUpErr) {
      setError(
        signUpErr.message.includes("already registered")
          ? "This email is already registered. Try signing in instead."
          : signUpErr.message
      );
      if (signUpErr.message.includes("already registered")) setMode("login");
      setLoading(false);
      return;
    }

    // Supabase may require email confirmation — auto sign-in as fallback
    if (!data.session) {
      const { error: signInErr } = await supabase.auth.signInWithPassword({ email, password });
      if (signInErr) {
        setError("Account created but auto sign-in failed. Please sign in manually.");
        setMode("login");
        setLoading(false);
        return;
      }
    }

    setMode("onboarding");
    setLoading(false);
  };

  /** Save profile fields (name, firm, rate) then trigger App.tsx data refresh. */
  const handleOnboarding = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      setError("Session expired. Please log in again.");
      setMode("login");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch("/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          full_name: fullName,
          firm_name: firmName,
          hourly_rate: parseInt(hourlyRate) || 2500,
          onboarded: true,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to save profile");
        setLoading(false);
        return;
      }

      onAuth(); // tell App.tsx to re-fetch profile + billing
    } catch {
      setError("Network error");
      setLoading(false);
    }
  };

  /** One-click demo: create account if needed, onboard, seed data, refresh. */
  const handleDemo = async () => {
    setLoading(true);
    setError("");

    // Try sign-in first (account may already exist)
    const { error: signInErr } = await supabase.auth.signInWithPassword({
      email: DEMO_EMAIL, password: DEMO_PASSWORD,
    });

    if (signInErr) {
      // First-time demo — create + onboard
      const { data, error: signUpErr } = await supabase.auth.signUp({
        email: DEMO_EMAIL, password: DEMO_PASSWORD,
      });
      if (signUpErr) {
        setError("Demo unavailable. Please sign up normally.");
        setLoading(false);
        return;
      }
      if (!data.session) {
        await supabase.auth.signInWithPassword({ email: DEMO_EMAIL, password: DEMO_PASSWORD });
      }

      // Set demo profile
      const { data: { session: s } } = await supabase.auth.getSession();
      if (s) {
        await fetch("/profile", {
          method: "PATCH",
          headers: { "Authorization": `Bearer ${s.access_token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ full_name: "Demo User", firm_name: "LexFlow Demo Firm", hourly_rate: 2500, onboarded: true }),
        });
      }
    }

    // Always seed fresh data (wipes old entries)
    const { data: { session: demoSession } } = await supabase.auth.getSession();
    if (demoSession) {
      await fetch("/demo/seed", {
        method: "POST",
        headers: { "Authorization": `Bearer ${demoSession.access_token}` },
      });
    }

    onAuth(); // tell App.tsx to re-fetch
  };

  /** Toggle between login and signup modes. */
  const toggleMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
  };

  // ── Render ───────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-background pointer-events-none" />

      <div className="relative w-full max-w-md space-y-8">
        {/* Brand header */}
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-2">
            <span className="text-3xl font-bold tracking-tighter uppercase text-primary" style={{ fontFamily: 'Inter, sans-serif' }}>LEX</span>
            <span className="text-2xl mx-[2px]" style={{ verticalAlign: 'middle' }}>⚖</span>
            <span className="text-3xl font-bold tracking-tighter uppercase text-primary" style={{ fontFamily: 'Inter, sans-serif' }}>FLOW</span>
          </div>
          <p className="text-sm text-muted-foreground tracking-wider uppercase">
            {mode === "onboarding" ? "Complete Your Profile" : "Billing Intelligence Platform"}
          </p>
        </div>

        {/* Auth card */}
        <div className="bento-card p-8 rounded-lg space-y-6">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20">
              {error}
            </div>
          )}

          {mode === "onboarding" ? (
            /* ── Onboarding form ── */
            <form onSubmit={handleOnboarding} className="space-y-5">
              <p className="text-sm text-muted-foreground font-light">
                Set your billing rate.
              </p>

              <div className="space-y-1">
                <label className={LABEL_CLASS}>Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                    required placeholder="e.g. Full Name" className={INPUT_CLASS} />
                </div>
              </div>

              <div className="space-y-1">
                <label className={LABEL_CLASS}>Firm Name <span className="text-muted-foreground/50">(optional)</span></label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input type="text" value={firmName} onChange={(e) => setFirmName(e.target.value)}
                    placeholder="e.g. Firm or Practice Name" className={INPUT_CLASS} />
                </div>
              </div>

              <div className="space-y-1">
                <label className={LABEL_CLASS}>Hourly Rate (ZAR)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-muted-foreground">R</span>
                  <input type="number" value={hourlyRate} onChange={(e) => setHourlyRate(e.target.value)}
                    required min="100" placeholder="2500" className={INPUT_CLASS} />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">Billable amounts will be calculated at this rate</p>
              </div>

              <button type="submit" disabled={loading} className={SUBMIT_CLASS}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {loading ? "Saving..." : "Start Billing"}
              </button>
            </form>
          ) : (
            /* ── Login / Signup form ── */
            <form onSubmit={mode === "login" ? handleLogin : handleSignup} className="space-y-5">
              <div className="space-y-1">
                <label className={LABEL_CLASS}>Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    required placeholder="advocate@firm.co.za" className={INPUT_CLASS} />
                </div>
              </div>

              <div className="space-y-1">
                <label className={LABEL_CLASS}>Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                    required minLength={6} placeholder="Min. 6 characters" className={INPUT_CLASS} />
                </div>
              </div>

              <button type="submit" disabled={loading} className={SUBMIT_CLASS}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {loading ? "Processing..." : mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>
          )}

          {/* Mode toggle + demo button (hidden during onboarding) */}
          {mode !== "onboarding" && (
            <div className="space-y-4">
              <div className="text-center">
                <button onClick={toggleMode}
                  className="text-xs text-muted-foreground hover:text-primary transition-colors font-medium">
                  {mode === "login" ? "No account? Create one" : "Already have an account? Sign in"}
                </button>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-primary/10" /></div>
                <div className="relative flex justify-center"><span className="bg-background px-3 text-[10px] text-muted-foreground uppercase tracking-widest">or</span></div>
              </div>

              <button type="button" onClick={handleDemo} disabled={loading}
                className="w-full py-3 border border-accent/30 text-primary font-headline tracking-tight hover:bg-accent/5 transition-all text-sm">
                {loading ? "Loading Demo..." : "Try Demo \u2014 No Sign Up Required"}
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-[10px] text-muted-foreground/50 uppercase tracking-[0.3em]">
          POPIA Compliant | HTTPS Secured
        </p>
      </div>
    </div>
  );
}
