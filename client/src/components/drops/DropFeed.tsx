/**
 * DropFeed Component
 * Renders a list of drops with loading and empty states
 */

import { Loader2, MessageSquare } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { DropCard } from './DropCard';
import type { Drop } from '@/types/drops';

interface DropFeedProps {
  drops: Drop[];
  isLoading: boolean;
  isAuthenticated: boolean;
  userId?: string;
  onToggleLike: (dropId: string, isLiked: boolean) => void;
  onDelete?: (dropId: string) => void;
  onAuthRequired?: () => void;
  isLikeLoading?: boolean;
  isDeleteLoading?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
}

/**
 * Loading skeleton for drops
 */
function DropsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-12" />
          </div>
          <div className="pl-10 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <div className="pl-10">
            <Skeleton className="h-8 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state component
 */
function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-secondary/50 p-4 mb-4">
        <MessageSquare className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm">{message}</p>
    </div>
  );
}

export function DropFeed({
  drops,
  isLoading,
  isAuthenticated,
  userId,
  onToggleLike,
  onDelete,
  onAuthRequired,
  isLikeLoading,
  isDeleteLoading,
  emptyTitle = 'No drops yet',
  emptyMessage = 'Be the first to share your market insights!',
}: DropFeedProps) {
  if (isLoading) {
    return <DropsSkeleton />;
  }

  if (drops.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />;
  }

  return (
    <div className="space-y-4">
      {drops.map((drop) => (
        <DropCard
          key={drop.id}
          drop={drop}
          isAuthenticated={isAuthenticated}
          isCurrentUser={userId === drop.user_id}
          onToggleLike={() => onToggleLike(drop.id, drop.user_has_liked)}
          onDelete={onDelete ? () => onDelete(drop.id) : undefined}
          onAuthRequired={onAuthRequired}
          isLikeLoading={isLikeLoading}
          isDeleteLoading={isDeleteLoading}
        />
      ))}
    </div>
  );
}

export default DropFeed;
