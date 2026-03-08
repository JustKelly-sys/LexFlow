import { ShieldCheck, LogOut, Mic, BookOpen } from "lucide-react";
import { NavLink } from "react-router-dom";

interface NavbarProps {
  userName?: string;
  firmName?: string;
  onLogout?: () => void;
  aiStatus?: 'ready' | 'processing' | 'error';
}

const STATUS_COLORS = {
  ready: 'bg-emerald-400',
  processing: 'bg-amber-400 animate-pulse',
  error: 'bg-red-400',
};

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-xs font-headline uppercase tracking-widest transition-colors ${
    isActive
      ? 'text-primary border-b border-primary pb-1'
      : 'text-muted-foreground hover:text-primary'
  }`;

export function Navbar({ userName, firmName, onLogout, aiStatus = 'ready' }: NavbarProps) {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-6 pointer-events-none bg-background/80 backdrop-blur-sm border-b border-primary/5">
      {/* Left: Logo + status dot */}
      <div className="flex items-center gap-2 pointer-events-auto cursor-pointer">
        <NavLink to="/" className="flex items-center gap-2">
          <span className="font-headline text-2xl font-bold tracking-tighter uppercase text-primary">LexFlow</span>
          <div
            className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${STATUS_COLORS[aiStatus]}`}
            title={aiStatus === 'ready' ? 'AI Ready' : aiStatus === 'processing' ? 'Processing...' : 'Connection Error'}
          />
        </NavLink>
      </div>

      {/* Center: Navigation links */}
      <div className="hidden md:flex items-center gap-8 pointer-events-auto">
        <NavLink to="/" className={linkClass} end>
          <span className="flex items-center gap-2">
            <Mic size={14} strokeWidth={1.5} />
            Dictate
          </span>
        </NavLink>
        <NavLink to="/ledger" className={linkClass}>
          <span className="flex items-center gap-2">
            <BookOpen size={14} strokeWidth={1.5} />
            Ledger
          </span>
        </NavLink>
      </div>

      {/* Right: User info + actions */}
      <div className="flex items-center gap-6 pointer-events-auto">
        {userName && (
          <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium text-primary">{userName}</span>
            {firmName && <span className="text-muted-foreground/50">| {firmName}</span>}
          </div>
        )}
        <button className="p-2 text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 text-xs font-medium uppercase tracking-widest">
          <ShieldCheck size={20} strokeWidth={1.5} />
          <span className="hidden sm:inline">FICA</span>
        </button>
        {onLogout && (
          <button
            onClick={onLogout}
            className="p-2 text-muted-foreground hover:text-destructive transition-colors"
            title="Sign Out"
          >
            <LogOut size={20} strokeWidth={1.5} />
          </button>
        )}
      </div>
    </nav>
  );
}
