import { ChevronRight, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
      {items[0]?.to && (
        <Link to={items[0].to} className="flex items-center gap-1 hover:text-primary transition-colors">
          <ArrowLeft size={14} strokeWidth={1.5} />
          {items[0].label}
        </Link>
      )}
      {items.slice(1).map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          <ChevronRight size={12} className="text-muted-foreground/40" />
          {item.to ? (
            <Link to={item.to} className="hover:text-primary transition-colors">{item.label}</Link>
          ) : (
            <span className="text-primary font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
