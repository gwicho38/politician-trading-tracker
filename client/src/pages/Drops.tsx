/**
 * Drops Page
 * Twitter-like social feed for trading insights with $TICKER mentions
 */

import { useState } from 'react';
import { MessageSquare, Sparkles, Radio, User, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useDrops } from '@/hooks/useDrops';
import { useDropsRealtime } from '@/hooks/useDropsRealtime';
import { useStrategyShowcase } from '@/hooks/useStrategyShowcase';
import { DropComposer, DropFeed } from '@/components/drops';
import { StrategyCard } from '@/components/showcase';
import { SidebarLayout } from '@/components/layouts/SidebarLayout';

export default function Drops() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('live');

  // Live drops feed
  const {
    drops: liveDrops,
    isLoading: isLoadingLive,
    isFetching: isFetchingLive,
    isAuthenticated,
    userId,
    toggleLike: toggleLikeLive,
    isLiking: isLikingLive,
    isUnliking: isUnlikingLive,
  } = useDrops('live');

  // My drops feed
  const {
    drops: myDrops,
    isLoading: isLoadingMyDrops,
    createDropAsync,
    isCreating,
    deleteDrop,
    isDeleting,
    toggleLike: toggleLikeMyDrops,
    isLiking: isLikingMyDrops,
    isUnliking: isUnlikingMyDrops,
  } = useDrops('my_drops');

  // User's strategies
  const {
    strategies,
    isLoading: isLoadingStrategies,
    toggleLike: toggleLikeStrategy,
    isLiking: isLikingStrategy,
    isUnliking: isUnlikingStrategy,
  } = useStrategyShowcase('recent');

  // Filter to user's own strategies
  const myStrategies = strategies.filter((s) => s.user_id === userId);

  // Real-time subscription for live tab
  useDropsRealtime();

  const handleAuthRequired = () => {
    toast({
      title: 'Sign in required',
      description: 'Please sign in to post or like drops.',
      action: (
        <Button variant="outline" size="sm" onClick={() => navigate('/auth')}>
          Sign In
        </Button>
      ),
    });
  };

  const handleCreateDrop = async (content: string) => {
    if (!isAuthenticated) {
      handleAuthRequired();
      return;
    }
    try {
      await createDropAsync({ content });
      toast({
        title: 'Drop posted!',
        description: 'Your drop is now live.',
      });
    } catch (error) {
      console.error('Failed to create drop:', error);
      toast({
        title: 'Failed to post',
        description: error instanceof Error ? error.message : 'Something went wrong',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteDrop = (dropId: string) => {
    deleteDrop(dropId);
    toast({
      title: 'Drop deleted',
      description: 'Your drop has been removed.',
    });
  };

  return (
    <SidebarLayout>
      {/* Page Header */}
      <div className="border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="container flex h-12 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Drops</h1>
            <span className="text-xs text-muted-foreground ml-2 hidden sm:inline">
              Share trading insights with the community
            </span>
          </div>

          {activeTab === 'live' && isFetchingLive && (
            <Badge variant="outline" className="animate-pulse">
              <Radio className="h-3 w-3 mr-1" />
              Live
            </Badge>
          )}
        </div>
      </div>

      <main className="container mx-auto px-4 py-6 max-w-3xl">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="live" className="flex items-center gap-2">
              <Radio className="h-4 w-4" />
              <span className="hidden sm:inline">Live</span> Drops
            </TabsTrigger>
            <TabsTrigger value="my-drops" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              My Drops
            </TabsTrigger>
            <TabsTrigger value="my-strategies" className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              <span className="hidden sm:inline">My</span> Strategies
            </TabsTrigger>
          </TabsList>

          {/* Live Drops Tab */}
          <TabsContent value="live" className="space-y-6">
            {/* Quick compose (collapsed) */}
            {isAuthenticated && (
              <DropComposer
                onSubmit={handleCreateDrop}
                isSubmitting={isCreating}
              />
            )}

            {!isAuthenticated && (
              <Alert>
                <AlertDescription className="flex items-center justify-between">
                  <span>Sign in to post drops and join the conversation.</span>
                  <Button size="sm" onClick={() => navigate('/auth')}>
                    Sign In
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            <DropFeed
              drops={liveDrops}
              isLoading={isLoadingLive}
              isAuthenticated={isAuthenticated}
              userId={userId}
              onToggleLike={toggleLikeLive}
              onAuthRequired={handleAuthRequired}
              isLikeLoading={isLikingLive || isUnlikingLive}
              emptyTitle="No drops yet"
              emptyMessage="Be the first to share your market insights!"
            />
          </TabsContent>

          {/* My Drops Tab */}
          <TabsContent value="my-drops" className="space-y-6">
            {isAuthenticated ? (
              <>
                <DropComposer
                  onSubmit={handleCreateDrop}
                  isSubmitting={isCreating}
                />

                <DropFeed
                  drops={myDrops}
                  isLoading={isLoadingMyDrops}
                  isAuthenticated={isAuthenticated}
                  userId={userId}
                  onToggleLike={toggleLikeMyDrops}
                  onDelete={handleDeleteDrop}
                  onAuthRequired={handleAuthRequired}
                  isLikeLoading={isLikingMyDrops || isUnlikingMyDrops}
                  isDeleteLoading={isDeleting}
                  emptyTitle="No drops yet"
                  emptyMessage="Share your first market insight above!"
                />
              </>
            ) : (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  <span>Sign in to view and manage your drops.</span>
                  <Button size="sm" onClick={() => navigate('/auth')}>
                    Sign In
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>

          {/* My Strategies Tab */}
          <TabsContent value="my-strategies" className="space-y-6">
            {isAuthenticated ? (
              <>
                {isLoadingStrategies ? (
                  <div className="grid gap-4">
                    {Array.from({ length: 2 }).map((_, i) => (
                      <Skeleton key={i} className="h-48 w-full rounded-lg" />
                    ))}
                  </div>
                ) : myStrategies.length > 0 ? (
                  <div className="grid gap-4">
                    {myStrategies.map((strategy) => (
                      <StrategyCard
                        key={strategy.id}
                        strategy={strategy}
                        isAuthenticated={isAuthenticated}
                        isCurrentUser={true}
                        onToggleLike={() =>
                          toggleLikeStrategy(strategy.id, strategy.user_has_liked)
                        }
                        onAuthRequired={handleAuthRequired}
                        isLikeLoading={isLikingStrategy || isUnlikingStrategy}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="rounded-full bg-secondary/50 p-4 mb-4">
                      <Sparkles className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-medium mb-1">No strategies yet</h3>
                    <p className="text-sm text-muted-foreground max-w-sm mb-4">
                      Create custom signal strategies in the Playground.
                    </p>
                    <Button onClick={() => navigate('/playground')}>
                      Go to Playground
                    </Button>
                  </div>
                )}
              </>
            ) : (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  <span>Sign in to view your saved strategies.</span>
                  <Button size="sm" onClick={() => navigate('/auth')}>
                    Sign In
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </SidebarLayout>
  );
}
