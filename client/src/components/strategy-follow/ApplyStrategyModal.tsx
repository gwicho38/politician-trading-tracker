import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Loader2,
  AlertTriangle,
  Play,
  Target,
  ArrowRightLeft,
} from 'lucide-react';
import { toast } from 'sonner';
import { useStrategyFollow } from '@/hooks/useStrategyFollow';
import { useAlpacaAccount } from '@/hooks/useAlpacaAccount';
import type { SignalWeights } from '@/types/signal-playground';

interface ApplyStrategyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyType: 'reference' | 'preset' | 'custom';
  presetId?: string;
  presetName?: string;
  customWeights?: SignalWeights;
}

export function ApplyStrategyModal({
  open,
  onOpenChange,
  strategyType,
  presetId,
  presetName,
  customWeights,
}: ApplyStrategyModalProps) {
  const { subscribe, isSubscribing, isFollowing, subscription } = useStrategyFollow();
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [syncExisting, setSyncExisting] = useState(false);

  // Get account info for the selected mode
  const { data: accountData, isLoading: isLoadingAccount } = useAlpacaAccount(tradingMode);

  // Strategy display name
  const strategyName =
    strategyType === 'reference'
      ? 'Reference Strategy'
      : strategyType === 'preset'
      ? presetName || 'Custom Preset'
      : 'Custom Weights';

  // Check if already following a different strategy
  const isFollowingDifferent =
    isFollowing &&
    subscription &&
    (subscription.strategy_type !== strategyType ||
      (strategyType === 'preset' && subscription.preset_id !== presetId));

  const handleApply = async () => {
    try {
      await subscribe({
        strategyType,
        presetId,
        customWeights,
        tradingMode,
        syncExistingPositions: syncExisting,
      });

      toast.success(`Now following ${strategyName}`, {
        description: `Your ${tradingMode} account will mirror this strategy.`,
      });
      onOpenChange(false);
    } catch (error) {
      toast.error('Failed to apply strategy', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Apply Strategy
          </DialogTitle>
          <DialogDescription>
            Configure how your account will follow this strategy
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Strategy Info */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div>
              <p className="text-sm text-muted-foreground">Strategy</p>
              <p className="font-medium">{strategyName}</p>
            </div>
            <Badge variant="outline" className="capitalize">
              {strategyType}
            </Badge>
          </div>

          {/* Warning if switching strategies */}
          {isFollowingDifferent && (
            <Alert variant="default">
              <ArrowRightLeft className="h-4 w-4" />
              <AlertDescription>
                You are currently following "{subscription?.preset_name || subscription?.strategy_type}".
                Applying this strategy will replace your current subscription.
              </AlertDescription>
            </Alert>
          )}

          {/* Trading Mode Selection */}
          <div className="space-y-3">
            <Label>Trading Mode</Label>
            <RadioGroup
              value={tradingMode}
              onValueChange={(value) => setTradingMode(value as 'paper' | 'live')}
              className="grid grid-cols-2 gap-4"
            >
              <div>
                <RadioGroupItem
                  value="paper"
                  id="paper"
                  className="peer sr-only"
                />
                <Label
                  htmlFor="paper"
                  className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Play className="mb-2 h-6 w-6" />
                  <span className="font-medium">Paper Trading</span>
                  <span className="text-xs text-muted-foreground">
                    Simulated money
                  </span>
                </Label>
              </div>

              <div>
                <RadioGroupItem
                  value="live"
                  id="live"
                  className="peer sr-only"
                />
                <Label
                  htmlFor="live"
                  className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <AlertTriangle className="mb-2 h-6 w-6 text-destructive" />
                  <span className="font-medium">Live Trading</span>
                  <span className="text-xs text-muted-foreground">
                    Real money
                  </span>
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Account Info */}
          {accountData?.account && (
            <div className="p-3 bg-muted/50 rounded-lg space-y-2">
              <p className="text-sm font-medium">Account Details</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <p className="text-muted-foreground">Equity</p>
                  <p className="font-mono">
                    ${parseFloat(accountData.account.equity).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Buying Power</p>
                  <p className="font-mono">
                    ${parseFloat(accountData.account.buying_power).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {isLoadingAccount && (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="ml-2 text-sm text-muted-foreground">
                Loading account...
              </span>
            </div>
          )}

          {/* Sync Existing Option */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="sync-existing">Sync existing positions</Label>
              <p className="text-xs text-muted-foreground">
                Adjust your current holdings to match the strategy
              </p>
            </div>
            <Switch
              id="sync-existing"
              checked={syncExisting}
              onCheckedChange={setSyncExisting}
            />
          </div>

          {/* Live Trading Warning */}
          {tradingMode === 'live' && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Warning:</strong> This will execute real trades with real
                money. Make sure you understand the strategy before proceeding.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubscribing}
          >
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            disabled={isSubscribing || isLoadingAccount}
            variant={tradingMode === 'live' ? 'destructive' : 'default'}
          >
            {isSubscribing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Applying...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Apply Strategy
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ApplyStrategyModal;
