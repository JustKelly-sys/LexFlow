import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { Loader2, ArrowRight, Mail, Lock, User, Building2 } from "lucide-react";

interface AuthPageProps {
  onAuth: () => void;
  initialMode?: Mode;
}

type Mode = "login" | "signup" | "onboarding";

export function AuthPage({ onAuth, initialMode = "login" }: AuthPageProps) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Onboarding fields
  const [fullName, setFullName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [hourlyRate, setHourlyRate] = useState("2500");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      if (error.message.includes("Invalid login")) {
        setError("Invalid email or password. If you're new, click 'Create one' below.");
      } else {
        setError(error.message);
      }
      setLoading(false);
    }
    // Don't call onAuth() here — supabase.auth.onAuthStateChange() in App.tsx
    // handles session changes. Calling onAuth() causes a race condition where
    // fetchProfile() runs with a stale null session.
  };

  const handleDemo = async () => {
    setLoading(true);
    setError("");
    const demoEmail = "demo@lexflow.app";
    const demoPw = "DemoLexFlow2026!";
    
    // Try to sign in first (demo account may already exist)
    const { error: signInError } = await supabase.auth.signInWithPassword({ email: demoEmail, password: demoPw });
    
    if (signInError) {
      // No account yet — create one + onboard
      const { data: signUpData, error: signUpError } = await supabase.auth.signUp({ email: demoEmail, password: demoPw });
      if (signUpError) {
        setError("Demo unavailable. Please sign up normally.");
        setLoading(false);
        return;
      }
      if (!signUpData.session) {
        await supabase.auth.signInWithPassword({ email: demoEmail, password: demoPw });
      }
      // Onboard demo user
      const { data: { session: s } } = await supabase.auth.getSession();
      if (s) {
        await fetch("/profile", {
          method: "PATCH",
          headers: { "Authorization": `Bearer ${s.access_token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ full_name: "Demo User", firm_name: "LexFlow Demo Firm", hourly_rate: 2500, onboarded: true }),
        });
      }
    }

    // ALWAYS seed fresh demo data (whether existing or new account)
    const { data: { session: demoSession } } = await supabase.auth.getSession();
    if (demoSession) {
      await fetch("/demo/seed", {
        method: "POST",
        headers: { "Authorization": `Bearer ${demoSession.access_token}` },
      });
    }
    onAuth();
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    const { data: signUpData, error: signUpError } = await supabase.auth.signUp({ email, password });
    if (signUpError) {
      if (signUpError.message.includes("already registered")) {
        setError("This email is already registered. Try signing in instead.");
        setMode("login");
      } else {
        setError(signUpError.message);
      }
      setLoading(false);
      return;
    }

    // If no session returned (email confirmation may be on), auto sign-in
    if (!signUpData.session) {
      const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) {
        setError("Account created but could not auto-sign in. Please sign in manually.");
        setMode("login");
        setLoading(false);
        return;
      }
    }

    // Session exists, go to onboarding
    setMode("onboarding");
    setLoading(false);
  };

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

      onAuth();
    } catch (err) {
      setError("Network error");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="absolute inset-0 topo-pattern opacity-30 pointer-events-none" />

      <div className="relative w-full max-w-md space-y-8">
        {/* Logo */}
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-2">
            <span className="font-headline text-3xl font-bold tracking-tighter uppercase text-primary">
              LexFlow
            </span>
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          </div>
          <p className="text-sm text-muted-foreground tracking-wider uppercase">
            {mode === "onboarding" ? "Complete Your Profile" : "Billing Intelligence Platform"}
          </p>
        </div>

        {/* Auth Card */}
        <div className="fluted-glass p-8 space-y-6">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20">
              {error}
            </div>
          )}

          {mode === "onboarding" ? (
            <form onSubmit={handleOnboarding} className="space-y-5">
              <p className="text-sm text-muted-foreground font-light">
                Set your billing rate.
              </p>

              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    placeholder="e.g. Full Name"
                    className="w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold">Firm Name <span className="text-muted-foreground/50">(optional)</span></label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={firmName}
                    onChange={(e) => setFirmName(e.target.value)}
                    placeholder="e.g. Firm or Practice Name"
                    className="w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold">Hourly Rate (ZAR)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-muted-foreground">R</span>
                  <input
                    type="number"
                    value={hourlyRate}
                    onChange={(e) => setHourlyRate(e.target.value)}
                    required
                    min="100"
                    placeholder="2500"
                    className="w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">AI will calculate billable amounts at this rate</p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-primary text-primary-foreground font-headline text-sm tracking-tight hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {loading ? "Saving..." : "Start Billing"}
              </button>
            </form>
          ) : (
            <form onSubmit={mode === "login" ? handleLogin : handleSignup} className="space-y-5">
              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="advocate@firm.co.za"
                    className="w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-semibold">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    placeholder="Min. 6 characters"
                    className="w-full pl-10 pr-4 py-3 bg-background border border-border text-sm font-light focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-primary text-primary-foreground font-headline text-sm tracking-tight hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {loading ? "Processing..." : mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>
          )}

          {mode !== "onboarding" && (
            <div className="space-y-4">
              <div className="text-center">
                <button
                  onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}
                  className="text-xs text-muted-foreground hover:text-primary transition-colors font-medium"
                >
                  {mode === "login" ? "No account? Create one" : "Already have an account? Sign in"}
                </button>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-primary/10" /></div>
                <div className="relative flex justify-center"><span className="bg-background px-3 text-[10px] text-muted-foreground uppercase tracking-widest">or</span></div>
              </div>

              <button
                type="button"
                onClick={handleDemo}
                disabled={loading}
                className="w-full py-3 border border-accent/30 text-primary font-headline tracking-tight hover:bg-accent/5 transition-all text-sm"
              >
                {loading ? "Loading Demo..." : "Try Demo — No Sign Up Required"}
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-[10px] text-muted-foreground/50 uppercase tracking-[0.3em]">
          FICA Compliant | End-to-End Encrypted
        </p>
      </div>
    </div>
  );
}
