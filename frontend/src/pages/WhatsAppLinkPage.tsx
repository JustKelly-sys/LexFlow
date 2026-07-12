import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Session } from '@supabase/supabase-js';

interface WhatsAppLinkPageProps {
  session: Session | null;
  code: string;
  onAuth?: () => void;
}

export function WhatsAppLinkPage({ session, code, onAuth }: WhatsAppLinkPageProps) {
  const [status, setStatus] = useState<'idle' | 'linking' | 'success' | 'error' | 'auth'>('idle');
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [message, setMessage] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    if (!session || !code) return;
    if (status === 'success' || status === 'linking') return;
    
    setStatus('linking');
    fetch('/whatsapp/link', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
          setStatus('success');
          setPhone(data.phone || '');
          setMessage('WhatsApp linked successfully!');
        } else {
          setStatus('error');
          setMessage(data.detail || 'Failed to link. Invalid or expired code.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Network error. Please try again.');
      });
  }, [session, code]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setAuthError(error.message);
      setAuthLoading(false);
    } else {
      if (onAuth) onAuth();
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });
    if (error) {
      setAuthError(error.message);
      setAuthLoading(false);
    } else {
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) {
        setAuthError('Account created! Please check your email to confirm, then come back here.');
        setAuthLoading(false);
      } else {
        if (onAuth) onAuth();
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="bento-card rounded-2xl p-8 sm:p-12 max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <div className="text-4xl">📱</div>
          <h1 className="font-serif text-2xl font-semibold text-primary tracking-tight">
            Connect WhatsApp
          </h1>
          <p className="text-sm text-muted-foreground">
            Link your WhatsApp to your LexFlow web account
          </p>
        </div>

        <div className="bg-secondary/50 rounded-xl p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Link Code</div>
          <div className="font-mono text-2xl font-bold text-primary tracking-[0.3em]">{code || '\u2014'}</div>
        </div>

        {!session && status !== 'auth' && status !== 'linking' && status !== 'success' ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Sign in or create an account to connect your WhatsApp.
            </p>
            <button
              onClick={() => setStatus('auth')}
              className="w-full py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            >
              Continue
            </button>
          </div>
        ) : !session && status === 'auth' ? (
          <div className="space-y-4">
            <div className="flex rounded-lg border border-border overflow-hidden">
              <button
                onClick={() => { setAuthMode('login'); setAuthError(''); }}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${authMode === 'login' ? 'bg-primary text-primary-foreground' : 'bg-transparent text-muted-foreground hover:bg-secondary/50'}`}
              >
                Sign In
              </button>
              <button
                onClick={() => { setAuthMode('signup'); setAuthError(''); }}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${authMode === 'signup' ? 'bg-primary text-primary-foreground' : 'bg-transparent text-muted-foreground hover:bg-secondary/50'}`}
              >
                Create Account
              </button>
            </div>

            <form onSubmit={authMode === 'login' ? handleLogin : handleSignUp} className="space-y-3 text-left">
              {authMode === 'signup' && (
                <div>
                  <label className="text-xs text-muted-foreground uppercase tracking-widest">Full Name</label>
                  <input
                    type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                    className="w-full mt-1 px-3 py-2 border border-border rounded-lg text-sm bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="e.g. Adv. T. Jafta" required
                  />
                </div>
              )}
              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-widest">Email</label>
                <input
                  type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-border rounded-lg text-sm bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="advocate@firm.co.za" required
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground uppercase tracking-widest">Password</label>
                <input
                  type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-border rounded-lg text-sm bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Min. 6 characters" required minLength={6}
                />
              </div>
              {authError && <p className="text-xs text-red-500">{authError}</p>}
              <button
                type="submit" disabled={authLoading}
                className="w-full py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {authLoading
                  ? (authMode === 'login' ? 'Signing in...' : 'Creating account...')
                  : (authMode === 'login' ? 'Sign In & Link' : 'Create Account & Link')}
              </button>
            </form>
          </div>
        ) : status === 'linking' ? (
          <div className="flex items-center justify-center gap-3 text-muted-foreground">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Linking your accounts...</span>
          </div>
        ) : status === 'success' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-2 text-emerald-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-lg font-semibold">{message}</span>
            </div>
            {phone && (
              <p className="text-sm text-muted-foreground">
                WhatsApp <span className="font-mono font-medium text-primary">+{phone}</span> is now connected.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Voice note entries will now appear on your web dashboard.
            </p>
            <a
              href="/"
              className="inline-block mt-2 px-6 py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            >
              Go to Dashboard
            </a>
          </div>
        ) : status === 'error' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-2 text-red-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">{message}</span>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 border border-border text-sm rounded-lg hover:bg-secondary/50 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : null}

        <div className="pt-4 border-t border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
            LexFlow &middot; Voice-to-billing for legal professionals
          </p>
        </div>
      </div>
    </div>
  );
}
