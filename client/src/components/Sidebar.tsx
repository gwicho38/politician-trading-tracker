import {
  LayoutDashboard,
  Users,
  TrendingUp,
  FileText,
  Target,
  Briefcase,
  BarChart3,
  ClipboardList,
  Clock,
  Settings,
  Globe,
  X,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useJurisdictions } from '@/hooks/useSupabaseData';
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeSection: string;
  onSectionChange: (section: string) => void;
  selectedJurisdiction?: string;
  onJurisdictionChange: (jurisdiction: string | undefined) => void;
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'trading-signals', label: 'Trading Signals', icon: Target },
  { id: 'trading-operations', label: 'Trading Operations', icon: Briefcase },
  { id: 'portfolio', label: 'Portfolio', icon: BarChart3 },
  { id: 'orders', label: 'Orders', icon: ClipboardList },
  { id: 'scheduled-jobs', label: 'Scheduled Jobs', icon: Clock },
  { id: 'trades', label: 'Recent Trades', icon: TrendingUp },
  { id: 'politicians', label: 'Politicians', icon: Users },
  { id: 'filings', label: 'Filings', icon: FileText },
];

const SyncStatus = () => {
  const [lastSync, setLastSync] = useState<Date>(new Date());
  const [timeAgo, setTimeAgo] = useState('just now');

  useEffect(() => {
    const interval = setInterval(() => {
      const diff = Math.floor((Date.now() - lastSync.getTime()) / 1000);
      if (diff < 60) {
        setTimeAgo(`${diff}s ago`);
      } else if (diff < 3600) {
        setTimeAgo(`${Math.floor(diff / 60)}m ago`);
      } else {
        setTimeAgo(`${Math.floor(diff / 3600)}h ago`);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [lastSync]);

  return (
    <div className="mt-4 rounded-lg bg-secondary/50 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Globe className="h-3 w-3" />
        <span>Last sync: {timeAgo}</span>
      </div>
      <div className="mt-1 h-1 w-full rounded-full bg-border">
        <div className="h-1 w-full rounded-full bg-primary animate-pulse" />
      </div>
    </div>
  );
};

const Sidebar = ({ isOpen, onClose, activeSection, onSectionChange, selectedJurisdiction, onJurisdictionChange }: SidebarProps) => {
  const { data: jurisdictions, isLoading } = useJurisdictions();

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-full w-72 border-r border-border/50 bg-sidebar transition-transform duration-300 lg:relative lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Mobile close button */}
          <div className="flex items-center justify-between p-4 lg:hidden">
            <span className="text-lg font-bold text-gradient">CapitolTrades</span>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            <div className="mb-6">
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Navigation
              </p>
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    onSectionChange(item.id);
                    onClose();
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    activeSection === item.id
                      ? "bg-primary/20 text-primary border border-primary/30"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                  {activeSection === item.id && (
                    <ChevronRight className="ml-auto h-4 w-4" />
                  )}
                </button>
              ))}
            </div>

            <div>
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Jurisdictions
              </p>
              <div className="space-y-1">
                {isLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  jurisdictions?.map((j) => (
                    <button
                      key={j.id}
                      onClick={() => {
                        onJurisdictionChange(selectedJurisdiction === j.id ? undefined : j.id);
                        onClose();
                      }}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200 hover:bg-secondary hover:text-foreground ${
                        selectedJurisdiction === j.id 
                          ? 'bg-primary/20 text-primary border border-primary/30' 
                          : 'text-muted-foreground'
                      }`}
                    >
                      <span className="text-base">{j.flag}</span>
                      {j.name}
                    </button>
                  ))
                )}
              </div>
            </div>
          </nav>

          {/* Footer */}
          <div className="border-t border-border/50 p-4">
            <Link 
              to="/admin" 
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-secondary hover:text-foreground"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>
            <SyncStatus />
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
