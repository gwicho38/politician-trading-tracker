import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Check, Loader2 } from 'lucide-react';
import { useStrategyFollow } from '@/hooks/useStrategyFollow';
import { useAuth } from '@/hooks/useAuth';
import { ApplyStrategyModal } from './ApplyStrategyModal';
import type { SignalWeights } from '@/types/signal-playground';

interface ApplyStrategyButtonProps {
  strategyType: 'reference' | 'preset' | 'custom';
  presetId?: string;
  presetName?: string;
  customWeights?: SignalWeights;
  variant?: 'default' | 'outline' | 'ghost' | 'secondary';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  showBadge?: boolean;
}

export function ApplyStrategyButton({
  strategyType,
  presetId,
  presetName,
  customWeights,
  variant = 'outline',
  size = 'sm',
  className = '',
  showBadge = true,
}: ApplyStrategyButtonProps) {
  const { user } = useAuth();
  const { subscription, isFollowing, isLoading } = useStrategyFollow();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Check if this specific strategy is currently being followed
  const isFollowingThis = isFollowing && subscription && (
    (strategyType === 'reference' && subscription.strategy_type === 'reference') ||
    (strategyType === 'preset' && subscription.strategy_type === 'preset' && subscription.preset_id === presetId) ||
    (strategyType === 'custom' && subscription.strategy_type === 'custom')
  );

  // Get button label based on state
  const getButtonLabel = () => {
    if (isLoading) return 'Loading...';
    if (isFollowingThis) return 'Following';
    return 'Apply Strategy';
  };

  const handleClick = () => {
    if (!user) {
      // TODO: Show sign-in toast
      return;
    }
    setIsModalOpen(true);
  };

  // If already following this strategy, show a different state
  if (isFollowingThis && showBadge) {
    return (
      <Badge variant="secondary" className={`gap-1 ${className}`}>
        <Check className="h-3 w-3" />
        Following
      </Badge>
    );
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={handleClick}
        disabled={isLoading}
        className={`gap-2 ${className}`}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {getButtonLabel()}
      </Button>

      <ApplyStrategyModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        strategyType={strategyType}
        presetId={presetId}
        presetName={presetName}
        customWeights={customWeights}
      />
    </>
  );
}

export default ApplyStrategyButton;
