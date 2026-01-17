/**
 * StrategyCard Component
 * Displays a strategy preset in the showcase grid
 */

import { Clock, Play, User as UserIcon, Code, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { LikeButton } from './LikeButton';
import { ApplyStrategyButton } from '@/components/strategy-follow';
import type { ShowcaseStrategy } from '@/types/signal-playground';

interface StrategyCardProps {
  strategy: ShowcaseStrategy;
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

  if (diffMonths > 0) return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;
  if (diffWeeks > 0) return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;
  if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffMinutes > 0) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  return 'Just now';
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

/**
 * Format weight as percentage
 */
function formatWeight(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function StrategyCard({
  strategy,
  isAuthenticated,
  isCurrentUser,
  onToggleLike,
  onDelete,
  onAuthRequired,
  isLikeLoading,
  isDeleteLoading,
}: StrategyCardProps) {
  const navigate = useNavigate();

  const handleTryInPlayground = () => {
    navigate(`/playground?preset=${strategy.id}`);
  };

  const handleEdit = () => {
    navigate(`/playground?preset=${strategy.id}&edit=true`);
  };

  // Key weights to display
  const keyWeights = [
    { label: 'Base', value: strategy.base_confidence },
    { label: 'Bipartisan', value: strategy.bipartisan_bonus },
    { label: '5+ Politicians', value: strategy.politician_count_5_plus },
  ];

  return (
    <Card className="flex flex-col h-full hover:shadow-lg transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg truncate">{strategy.name}</CardTitle>
              {strategy.user_lambda && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="outline" className="text-xs shrink-0 gap-1">
                      <Code className="h-3 w-3" />
                      Transform
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Includes custom signal transform code</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-sm text-muted-foreground">
              <UserIcon className="h-3.5 w-3.5" />
              <span className="truncate">
                {getDisplayName(strategy.author_email)}
              </span>
              {isCurrentUser && (
                <Badge variant="secondary" className="text-xs ml-1">
                  You
                </Badge>
              )}
            </div>
          </div>
        </div>
        {strategy.description && (
          <CardDescription className="line-clamp-2 mt-2">
            {strategy.description}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="flex-1 pb-2">
        {/* Key weights preview */}
        <div className="flex flex-wrap gap-2 text-xs">
          {keyWeights.map(({ label, value }) => (
            <Badge key={label} variant="outline" className="font-normal">
              {label}: {formatWeight(value)}
            </Badge>
          ))}
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between pt-2 border-t">
        <div className="flex items-center gap-3">
          <LikeButton
            likesCount={strategy.likes_count}
            isLiked={strategy.user_has_liked}
            isAuthenticated={isAuthenticated}
            isLoading={isLikeLoading}
            onToggle={onToggleLike}
            onAuthRequired={onAuthRequired}
          />
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>{formatRelativeTime(strategy.created_at)}</span>
          </div>
        </div>

        {isCurrentUser ? (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleEdit}>
              Edit
            </Button>
            {onDelete && (
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={onDelete}
                disabled={isDeleteLoading}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleTryInPlayground}>
              <Play className="h-4 w-4 mr-1" />
              Try
            </Button>
            <ApplyStrategyButton
              strategyType="preset"
              presetId={strategy.id}
              presetName={strategy.name}
              size="sm"
              showBadge={false}
            />
          </div>
        )}
      </CardFooter>
    </Card>
  );
}

export default StrategyCard;
