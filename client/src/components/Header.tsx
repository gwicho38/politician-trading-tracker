import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Menu, LogOut, User, UserX, Shield, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { supabase } from '@/integrations/supabase/client';
import { useAdmin } from '@/hooks/useAdmin';
import { useAuth } from '@/hooks/useAuth';
import { HeaderSyncStatus } from '@/components/SyncStatus';
import { GlobalSearch } from '@/components/GlobalSearch';
import { safeClearByPrefix } from '@/lib/safeStorage';

interface HeaderProps {
  onMenuClick?: () => void;
}

const Header = ({ onMenuClick }: HeaderProps) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isAdmin } = useAdmin();
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  const handleSignOut = () => {
    // Don't await signOut - it can block due to Supabase client issues
    // Instead, just clear localStorage and reload
    supabase.auth.signOut().catch(console.error);

    // Clear all Supabase auth tokens from localStorage (with error handling)
    safeClearByPrefix('sb-');

    // Navigate home and reload to clear all cached state
    navigate('/');
    window.location.reload();
  };

  const getDisplayName = () => {
    if (!user) return '';
    
    // Check for wallet address in metadata
    const walletAddress = user.user_metadata?.wallet_address;
    if (walletAddress) {
      return `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`;
    }
    
    return user.email?.split('@')[0] || 'User';
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          {onMenuClick && (
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={onMenuClick}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}

          <Link to="/" className="flex items-center gap-3">
            <div className="relative">
              <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30">
                <span className="text-xl">📊</span>
              </div>
              <div className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-success animate-pulse" />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-gradient">Gov</span>
                <span className="text-foreground">Market</span>
              </h1>
              <p className="text-xs text-muted-foreground -mt-0.5">
                Politician Trading Tracker
              </p>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {/* Desktop search */}
          <div className="hidden md:block">
            <GlobalSearch />
          </div>

          {/* Mobile search button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileSearchOpen(true)}
            aria-label="Search"
          >
            <Search className="h-5 w-5" />
          </Button>

          <HeaderSyncStatus />

          {/* COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready */}
          {/* {user && <NotificationBell />} */}

          {/* {isAdmin && (
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => navigate('/admin')}
            >
              <Shield className="h-4 w-4" />
              <span className="hidden sm:inline">Admin</span>
            </Button>
          )} */}

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">{getDisplayName()}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem className="text-muted-foreground text-xs">
                  {user.email}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleSignOut} className="text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => navigate('/auth')}
              title="Sign in to access all features"
            >
              <UserX className="h-4 w-4 text-muted-foreground" />
              <span className="hidden sm:inline">Sign In</span>
            </Button>
          )}
        </div>
      </div>

      {/* Mobile search dialog */}
      <Dialog open={mobileSearchOpen} onOpenChange={setMobileSearchOpen}>
        <DialogContent className="top-[10%] translate-y-0 sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Search</DialogTitle>
          </DialogHeader>
          <GlobalSearch
            fullWidth
            onResultSelect={() => setMobileSearchOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </header>
  );
};

export default Header;
