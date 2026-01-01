/**
 * LikeButton Component
 * Heart icon button for liking strategies with optimistic updates
 */

import { Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface LikeButtonProps {
  likesCount: number;
  isLiked: boolean;
  isAuthenticated: boolean;
  isLoading?: boolean;
  onToggle: () => void;
  onAuthRequired?: () => void;
}

export function LikeButton({
  likesCount,
  isLiked,
  isAuthenticated,
  isLoading = false,
  onToggle,
  onAuthRequired,
}: LikeButtonProps) {
  const handleClick = () => {
    if (!isAuthenticated) {
      onAuthRequired?.();
      return;
    }
    onToggle();
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn(
        'gap-1.5 h-8 px-2',
        isLiked && 'text-red-500 hover:text-red-600'
      )}
      onClick={handleClick}
      disabled={isLoading}
    >
      <Heart
        className={cn(
          'h-4 w-4 transition-all',
          isLiked && 'fill-current',
          isLoading && 'animate-pulse'
        )}
      />
      <span className="text-sm font-medium tabular-nums">{likesCount}</span>
    </Button>
  );
}

export default LikeButton;
