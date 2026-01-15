/**
 * DropCard Component
 * Displays a single drop (post) in the feed
 */

import { Trash2, User as UserIcon } from 'lucide-react';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { LikeButton } from '@/components/showcase/LikeButton';
import { DropContent } from './DropContent';
import type { Drop } from '@/types/drops';

interface DropCardProps {
  drop: Drop;
  isAuthenticated: boolean;
  isCurrentUser: boolean;
  onToggleLike: () => void;
  onDelete?: () => void;
  onAuthRequired?: () => void;
  isLikeLoading?: boolean;
  isDeleteLoading?: boolean;
}

/**
 * Format relative time (e.g., "2 days ago", "3 hours ago")
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);

  if (diffMonths > 0) return `${diffMonths}mo`;
  if (diffWeeks > 0) return `${diffWeeks}w`;
  if (diffDays > 0) return `${diffDays}d`;
  if (diffHours > 0) return `${diffHours}h`;
  if (diffMinutes > 0) return `${diffMinutes}m`;
  return 'now';
}

/**
 * Get display name from email
 */
function getDisplayName(email: string | null): string {
  if (!email) return 'Anonymous';
  const localPart = email.split('@')[0];
  // Capitalize first letter
  return localPart.charAt(0).toUpperCase() + localPart.slice(1);
}

export function DropCard({
  drop,
  isAuthenticated,
  isCurrentUser,
  onToggleLike,
  onDelete,
  onAuthRequired,
  isLikeLoading,
  isDeleteLoading,
}: DropCardProps) {
  return (
    <Card className="hover:bg-accent/5 transition-colors">
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-center gap-2 text-sm">
          <div className="flex items-center justify-center h-8 w-8 rounded-full bg-secondary">
            <UserIcon className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="font-medium truncate">
              {getDisplayName(drop.author_email)}
            </span>
            {isCurrentUser && (
              <Badge variant="secondary" className="text-xs h-5">
                You
              </Badge>
            )}
            <span className="text-muted-foreground">·</span>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-muted-foreground text-xs hover:underline cursor-default">
                  {formatRelativeTime(drop.created_at)}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                {new Date(drop.created_at).toLocaleString()}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-2 pl-14">
        <DropContent content={drop.content} />
      </CardContent>

      <CardFooter className="px-4 pb-3 pt-1 pl-14 flex items-center justify-between">
        <LikeButton
          likesCount={drop.likes_count}
          isLiked={drop.user_has_liked}
          isAuthenticated={isAuthenticated}
          isLoading={isLikeLoading}
          onToggle={onToggleLike}
          onAuthRequired={onAuthRequired}
        />

        {isCurrentUser && onDelete && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-muted-foreground hover:text-destructive"
                disabled={isDeleteLoading}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this drop?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. This drop will be permanently removed.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={onDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </CardFooter>
    </Card>
  );
}

export default DropCard;
