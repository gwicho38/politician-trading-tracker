import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  X,
  ChevronRight,
  Sliders,
  Sparkles,
  Wallet,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SidebarSyncStatus } from '@/components/SyncStatus';
import Header from '@/components/Header';

// Standalone pages with their own routes
const standalonePages = [
  { path: '/trading', label: 'Trading', icon: Wallet },
  { path: '/reference-portfolio', label: 'Reference Strategy', icon: Activity },
  { path: '/playground', label: 'Signal Playground', icon: Sliders },
  { path: '/showcase', label: 'Strategy Showcase', icon: Sparkles },
];

interface SidebarLayoutProps {
  children: React.ReactNode;
}

export function SidebarLayout({ children }: SidebarLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const currentPath = location.pathname;

  const isActive = (path: string) => {
    if (path === '/') {
      return currentPath === '/';
    }
    return currentPath === path;
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-full w-72 border-r border-border/50 bg-sidebar transition-transform duration-300 lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Mobile close button */}
          <div className="flex items-center justify-between p-4 lg:hidden">
            <span className="text-lg font-bold text-gradient">GovMarket</span>
            <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Desktop logo */}
          <div className="hidden lg:flex items-center gap-3 p-4 border-b border-border/50">
            <div className="relative">
              <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30">
                <span className="text-xl">📊</span>
              </div>
              <div className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-success animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-gradient">Gov</span>
                <span className="text-foreground">Market</span>
              </h1>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            <div className="mb-6">
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Navigation
              </p>

              {/* Dashboard link */}
              <Link
                to="/"
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  currentPath === '/'
                    ? "bg-primary/20 text-primary border border-primary/30"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
                {currentPath === '/' && <ChevronRight className="ml-auto h-4 w-4" />}
              </Link>

              {/* Standalone pages */}
              {standalonePages.map((page) => (
                <Link
                  key={page.path}
                  to={page.path}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive(page.path)
                      ? "bg-primary/20 text-primary border border-primary/30"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  <page.icon className="h-4 w-4" />
                  {page.label}
                  {isActive(page.path) && <ChevronRight className="ml-auto h-4 w-4" />}
                </Link>
              ))}
            </div>
          </nav>

          {/* Footer */}
          <div className="border-t border-border/50 p-4">
            <SidebarSyncStatus />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <Header onMenuClick={() => setSidebarOpen(true)} />

        {/* Page content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}

export default SidebarLayout;
