import { User, ShieldCheck, Search } from "lucide-react";

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-6 pointer-events-none">
      <div className="flex items-center gap-2 pointer-events-auto cursor-pointer">
        <span className="font-headline text-2xl font-bold tracking-tighter uppercase text-primary">LexFlow</span>
        <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
      </div>

      <div className="flex items-center gap-6 pointer-events-auto">
        <button className="p-2 text-muted-foreground hover:text-primary transition-colors">
          <Search size={20} strokeWidth={1.5} />
        </button>
        <button className="p-2 text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 text-xs font-medium uppercase tracking-widest">
          <ShieldCheck size={20} strokeWidth={1.5} />
          <span className="hidden sm:inline">FICA Compliant</span>
        </button>
        <button className="p-2 border border-primary/10 rounded-full hover:bg-white transition-all shadow-sm">
          <User size={20} strokeWidth={1.5} />
        </button>
      </div>
    </nav>
  );
}
