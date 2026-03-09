import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Session } from '@supabase/supabase-js';

interface WhatsAppLinkPageProps {
  session: Session | null;
}

export function WhatsAppLinkPage({ session }: WhatsAppLinkPageProps) {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'linking' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [phone, setPhone] = useState('');

  useEffect(() => {
    if (!session || !code) return;
    
    // Auto-link when user is authenticated
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
          setMessage(data.detail || 'Failed to link. Check your code and try again.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Network error. Please try again.');
      });
  }, [session, code]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="bento-card rounded-2xl p-8 sm:p-12 max-w-md w-full text-center space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="text-4xl">📱</div>
          <h1 className="font-serif text-2xl font-semibold text-primary tracking-tight">
            Connect WhatsApp
          </h1>
          <p className="text-sm text-muted-foreground">
            Link your WhatsApp to your LexFlow web account
          </p>
        </div>

        {/* Link Code Display */}
        <div className="bg-secondary/50 rounded-xl p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">
            Link Code
          </div>
          <div className="font-mono text-2xl font-bold text-primary tracking-[0.3em]">
            {code || '—'}
          </div>
        </div>

        {/* Status */}
        {!session ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-2 text-amber-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">Please log in first</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Log in to your LexFlow account, then come back to this page to complete the link.
            </p>
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
                WhatsApp number <span className="font-mono font-medium text-primary">+{phone}</span> is now connected.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              All your voice note entries will now appear on your web dashboard.
              Any previous unlinked entries have been claimed to your account.
            </p>
            <button
              onClick={() => navigate('/')}
              className="mt-2 px-6 py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
            >
              Go to Dashboard
            </button>
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

        {/* Footer */}
        <div className="pt-4 border-t border-border">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
            LexFlow · Voice-to-billing for legal professionals
          </p>
        </div>
      </div>
    </div>
  );
}
