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
  X,
  ChevronRight,
  Loader2,
  Sliders,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useJurisdictions } from '@/hooks/useSupabaseData';
import { Link } from 'react-router-dom';
import { SidebarSyncStatus } from '@/components/SyncStatus';

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
  { id: 'politicians', label: 'Politicians', icon: Users },
  { id: 'filings', label: 'Filings', icon: FileText },
  // COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready
  // { id: 'trading-signals', label: 'Trading Signals', icon: Target },
  // { id: 'trading-operations', label: 'Trading Operations', icon: Briefcase },
  // { id: 'portfolio', label: 'Portfolio', icon: BarChart3 },
  // { id: 'orders', label: 'Orders', icon: ClipboardList },
  // { id: 'scheduled-jobs', label: 'Scheduled Jobs', icon: Clock },
  // { id: 'trades', label: 'Recent Trades', icon: TrendingUp },
];

// Standalone pages with their own routes
const standalonePages = [
  { path: '/playground', label: 'Signal Playground', icon: Sliders },
  { path: '/showcase', label: 'Strategy Showcase', icon: Sparkles },
];

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
            <span className="text-lg font-bold text-gradient">GovMarket</span>
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

              {/* Standalone pages */}
              {standalonePages.map((page) => (
                <Link
                  key={page.path}
                  to={page.path}
                  onClick={onClose}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  <page.icon className="h-4 w-4" />
                  {page.label}
                </Link>
              ))}
            </div>

            {/* Jurisdictions Filter */}
            <div className="mt-4">
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Filter by Chamber
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
                      className={cn(
                        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200",
                        selectedJurisdiction === j.id
                          ? 'bg-primary/20 text-primary border border-primary/30'
                          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                      )}
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
            {/* COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready */}
            {/* <Link
              to="/admin"
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-secondary hover:text-foreground"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link> */}
            <SidebarSyncStatus />
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
