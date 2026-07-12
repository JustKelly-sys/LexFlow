import { useState } from "react";
import { ShieldCheck, LogOut, Mic, BookOpen, BarChart3, Menu, X } from "lucide-react";
import { NavLink, Link } from "react-router-dom";

interface NavbarProps {
  userName?: string;
  firmName?: string;
  onLogout?: () => void;
  aiStatus?: 'ready' | 'processing' | 'error';
}

const STATUS_COLORS: Record<string, string> = {
  ready: 'bg-accent',
  processing: 'bg-amber-400 animate-pulse',
  error: 'bg-red-400',
};

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-medium transition-colors ${
    isActive
      ? 'bg-secondary text-primary'
      : 'text-muted-foreground hover:text-primary hover:bg-muted'
  }`;

const mobileLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 mx-3 my-1 px-4 py-3 rounded-full text-sm font-medium transition-colors ${
    isActive ? 'bg-secondary text-primary' : 'text-muted-foreground hover:text-primary hover:bg-muted'
  }`;

export function Navbar({ userName, firmName, onLogout, aiStatus = 'ready' }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/90 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-8 py-3.5">
        <Link to="/" className="flex items-center gap-2">
          <span className="font-serif text-[1.6rem] leading-none text-primary tracking-tight">
            LexFlow<span className="text-accent">.</span>
          </span>
          <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${STATUS_COLORS[aiStatus]}`} />
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1 bg-card border border-border rounded-full p-1">
          <NavLink to="/" className={linkClass} end>
            <BarChart3 size={13} strokeWidth={1.5} /> Dashboard
          </NavLink>
          <NavLink to="/dictate" className={linkClass}>
            <Mic size={13} strokeWidth={1.5} /> Dictate
          </NavLink>
          <NavLink to="/ledger" className={linkClass}>
            <BookOpen size={13} strokeWidth={1.5} /> Ledger
          </NavLink>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          {userName && (
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-primary">{userName}</span>
              {firmName && <span className="text-muted-foreground/50">| {firmName}</span>}
            </div>
          )}
          <NavLink to="/fica" className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-medium transition-colors ${
              isActive ? 'bg-secondary text-primary' : 'text-muted-foreground hover:text-primary hover:bg-muted'
            }`
          }>
            <ShieldCheck size={16} strokeWidth={1.5} /> <span className="hidden sm:inline">Quality</span>
          </NavLink>
          {onLogout && (
            <button onClick={onLogout} className="p-2 rounded-full text-muted-foreground hover:text-destructive hover:bg-muted transition-colors" title="Sign Out">
              <LogOut size={16} strokeWidth={1.5} />
            </button>
          )}
          {/* Mobile hamburger */}
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2 rounded-full text-muted-foreground hover:text-primary hover:bg-muted transition-colors">
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-md pb-2">
          <NavLink to="/" className={mobileLinkClass} end onClick={() => setMobileOpen(false)}>
            <BarChart3 size={16} /> Dashboard
          </NavLink>
          <NavLink to="/dictate" className={mobileLinkClass} onClick={() => setMobileOpen(false)}>
            <Mic size={16} /> Dictate
          </NavLink>
          <NavLink to="/ledger" className={mobileLinkClass} onClick={() => setMobileOpen(false)}>
            <BookOpen size={16} /> Ledger
          </NavLink>
          <NavLink to="/fica" className={mobileLinkClass} onClick={() => setMobileOpen(false)}>
            <ShieldCheck size={16} /> Data Quality
          </NavLink>
          {userName && (
            <div className="px-6 py-3 text-xs text-muted-foreground border-t border-border">
              {userName}{firmName ? ` | ${firmName}` : ''}
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
