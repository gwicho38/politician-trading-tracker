/**
 * Showcase Page
 * Public gallery of community-created signal weight strategies
 */

import { useState } from 'react';
import { ArrowLeft, Sparkles, TrendingUp, Clock, AlertCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { useStrategyShowcase, SortOption } from '@/hooks/useStrategyShowcase';
import { StrategyCard } from '@/components/showcase';

export default function Showcase() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [sortBy, setSortBy] = useState<SortOption>('recent');

  const {
    strategies,
    isLoading,
    error,
    isAuthenticated,
    userId,
    toggleLike,
    isLiking,
    isUnliking,
  } = useStrategyShowcase(sortBy);

  const handleAuthRequired = () => {
    toast({
      title: 'Sign in required',
      description: 'Please sign in to like strategies.',
      action: (
        <Button variant="outline" size="sm" onClick={() => navigate('/auth')}>
          Sign In
        </Button>
      ),
    });
  };

  const handleSortChange = (value: string) => {
    setSortBy(value as SortOption);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="container flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <div>
                <h1 className="text-lg font-semibold">Strategy Showcase</h1>
                <p className="text-xs text-muted-foreground">
                  Community-created signal strategies
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Sort selector */}
            <Select value={sortBy} onValueChange={handleSortChange}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    <span>Most Recent</span>
                  </div>
                </SelectItem>
                <SelectItem value="popular">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    <span>Most Liked</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>

            {/* Create strategy CTA */}
            <Button onClick={() => navigate('/playground')}>
              Create Strategy
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container px-4 py-8">
        {/* Error state */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load strategies: {error.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-32 w-full rounded-lg" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && strategies.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Sparkles className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h2 className="text-xl font-semibold mb-2">No strategies yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              Be the first to share a strategy! Create custom signal weights in the
              playground and share them with the community.
            </p>
            <Button onClick={() => navigate('/playground')}>
              Create Your First Strategy
            </Button>
          </div>
        )}

        {/* Strategy grid */}
        {!isLoading && strategies.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {strategies.map((strategy) => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                isAuthenticated={isAuthenticated}
                isCurrentUser={userId === strategy.user_id}
                onToggleLike={() => toggleLike(strategy.id, strategy.user_has_liked)}
                onAuthRequired={handleAuthRequired}
                isLikeLoading={isLiking || isUnliking}
              />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-background/50 backdrop-blur-xl py-4 mt-auto">
        <div className="container px-4 text-center text-sm text-muted-foreground">
          <p>
            Share your strategies with the community and discover new approaches
          </p>
        </div>
      </footer>
    </div>
  );
}
