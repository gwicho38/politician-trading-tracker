import { useState, useEffect, useCallback, useRef } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  ExternalLink,
  Loader2,
  User,
  Sparkles,
  AlertCircle,
  BarChart3,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { usePoliticianDetail, type Politician } from '@/hooks/useSupabaseData';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn } from '@/lib/utils';
// Use public client to avoid auth blocking issues
import { supabasePublic as supabase } from '@/integrations/supabase/client';
import { logError } from '@/lib/logger';

// Timeout for profile generation (15 seconds)
const PROFILE_FETCH_TIMEOUT = 15000;

interface PoliticianProfileModalProps {
  politician: Politician | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ProfileBio {
  bio: string;
  source: 'ollama' | 'fallback';
  isLoading: boolean;
  error?: string;
}

export function PoliticianProfileModal({
  politician,
  open,
  onOpenChange,
}: PoliticianProfileModalProps) {
  const { data: detail, isLoading: detailLoading } = usePoliticianDetail(politician?.id ?? null);
  const [profileBio, setProfileBio] = useState<ProfileBio>({
    bio: '',
    source: 'fallback',
    isLoading: false,
  });

  // Track active request to abort if modal closes
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const fetchProfileBio = useCallback(async (pol: Politician, det: NonNullable<typeof detail>) => {
    // Abort any in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setProfileBio({ bio: '', source: 'fallback', isLoading: true });

    // Create a timeout promise
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Request timeout')), PROFILE_FETCH_TIMEOUT);
    });

    try {
      const fetchPromise = supabase.functions.invoke('politician-profile', {
        body: {
          politician: {
            name: pol.name,
            party: pol.party,
            chamber: pol.chamber,
            state: pol.state || pol.jurisdiction_id,
            totalTrades: pol.total_trades,
            totalVolume: pol.total_volume,
            topTickers: det.topTickers?.map(t => t.ticker),
          },
        },
      });

      // Race between fetch and timeout
      const { data, error } = await Promise.race([fetchPromise, timeoutPromise]);

      // Check if request was aborted or component unmounted
      if (controller.signal.aborted || !isMountedRef.current) return;

      if (error) {
        logError('Profile fetch error', 'politician-profile', undefined, { error: error.message });
        setProfileBio({
          bio: generateClientFallbackBio(pol, det),
          source: 'fallback',
          isLoading: false,
          error: 'Could not fetch AI profile',
        });
        return;
      }

      setProfileBio({
        bio: data.bio || generateClientFallbackBio(pol, det),
        source: data.source || 'fallback',
        isLoading: false,
      });
    } catch (err) {
      // Check if request was aborted or component unmounted
      if (controller.signal.aborted || !isMountedRef.current) return;

      const errorMessage = err instanceof Error ? err.message : 'Network error';
      logError('Profile fetch error', 'politician-profile', err instanceof Error ? err : undefined);
      setProfileBio({
        bio: generateClientFallbackBio(pol, det),
        source: 'fallback',
        isLoading: false,
        error: errorMessage === 'Request timeout' ? 'Profile generation timed out' : 'Network error',
      });
    }
  }, []);

  // Fetch AI bio when modal opens and detail is available
  useEffect(() => {
    if (open && politician && detail) {
      fetchProfileBio(politician, detail);
    }
  }, [open, politician, detail, fetchProfileBio]);

  // Reset bio and abort when modal closes
  useEffect(() => {
    if (!open) {
      abortControllerRef.current?.abort();
      setProfileBio({ bio: '', source: 'fallback', isLoading: false });
    }
  }, [open]);

  const generateClientFallbackBio = (pol: Politician, det: typeof detail): string => {
    const partyFull = pol.party === 'D' ? 'Democratic' :
                      pol.party === 'R' ? 'Republican' :
                      pol.party || 'Independent';

    const chamberFull = pol.chamber?.toLowerCase().includes('rep') ? 'Representative' :
                        pol.chamber?.toLowerCase().includes('sen') ? 'Senator' :
                        pol.chamber || 'Member of Congress';

    const tickersList = det?.topTickers?.slice(0, 3).map(t => t.ticker).join(', ');
    const tickersNote = tickersList ? ` Their most frequently traded securities include ${tickersList}.` : '';

    const volumeFormatted = formatCurrency(pol.total_volume);

    return `${pol.name} is a ${partyFull} ${chamberFull} from ${pol.state || 'the United States'}. According to public financial disclosure filings, they have reported ${pol.total_trades} trades with an estimated trading volume of ${volumeFormatted}.${tickersNote}`;
  };

  if (!politician) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] sm:max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="pb-4 border-b">
          <div className="flex items-start gap-4">
            {/* Avatar */}
            <div className="flex-shrink-0 h-16 w-16 rounded-full bg-secondary flex items-center justify-center text-xl font-bold text-muted-foreground">
              {politician.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || '??'}
            </div>

            <div className="flex-1 min-w-0">
              <DialogTitle className="text-xl flex items-center gap-2 flex-wrap">
                {politician.name}
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    getPartyBg(politician.party),
                    getPartyColor(politician.party)
                  )}
                >
                  {politician.party}
                </Badge>
              </DialogTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {politician.chamber} {politician.state && `• ${politician.state}`}
              </p>
            </div>
          </div>
        </DialogHeader>

        {detailLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : detail ? (
          <div className="flex-1 overflow-y-auto space-y-6 py-4">
            {/* AI Bio Section */}
            <div className="rounded-lg border border-border/50 p-4 bg-secondary/20">
              <div className="flex items-center gap-2 mb-3">
                {profileBio.source === 'ollama' ? (
                  <Sparkles className="h-4 w-4 text-primary" />
                ) : (
                  <User className="h-4 w-4 text-muted-foreground" />
                )}
                <h4 className="text-sm font-semibold">
                  {profileBio.source === 'ollama' ? 'AI-Generated Profile' : 'Profile Summary'}
                </h4>
                {profileBio.source === 'ollama' && (
                  <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/30">
                    AI
                  </Badge>
                )}
              </div>

              {profileBio.isLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating profile...</span>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {profileBio.bio}
                </p>
              )}

              {profileBio.error && (
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <AlertCircle className="h-3 w-3" />
                  <span>Using cached profile data</span>
                </div>
              )}
            </div>

            {/* Trading Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
              <div className="rounded-lg bg-secondary/50 p-2 sm:p-3 text-center">
                <p className="text-lg sm:text-xl font-bold">{detail.total_trades}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div className="rounded-lg bg-success/10 p-2 sm:p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <TrendingUp className="h-3 w-3 text-success" aria-hidden="true" />
                  <p className="text-lg sm:text-xl font-bold text-success">{detail.buyCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Buys</p>
              </div>
              <div className="rounded-lg bg-destructive/10 p-2 sm:p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <TrendingDown className="h-3 w-3 text-destructive" aria-hidden="true" />
                  <p className="text-lg sm:text-xl font-bold text-destructive">{detail.sellCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Sells</p>
              </div>
              <div className="rounded-lg bg-primary/10 p-2 sm:p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Wallet className="h-3 w-3 text-primary" aria-hidden="true" />
                  <p className="text-lg sm:text-xl font-bold text-primary">{detail.holdingCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Holdings</p>
              </div>
            </div>

            {/* Total Volume */}
            <div className="rounded-lg border p-4">
              <p className="text-sm text-muted-foreground">Total Trading Volume</p>
              <p className="text-2xl font-bold font-mono">
                {formatCurrency(detail.total_volume)}
              </p>
            </div>

            {/* Top Tickers */}
            {detail.topTickers.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Most Traded Tickers
                </h4>
                <div className="flex flex-wrap gap-2">
                  {detail.topTickers.map((t) => (
                    <Badge key={t.ticker} variant="secondary" className="font-mono">
                      {t.ticker}
                      <span className="ml-1 text-muted-foreground">({t.count})</span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Trades */}
            {detail.recentTrades.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3">Recent Trades</h4>
                <div className="space-y-2">
                  {detail.recentTrades.slice(0, 5).map((trade) => (
                    <div
                      key={trade.id}
                      className="flex items-center justify-between rounded-lg border p-3 text-sm"
                    >
                      <div className="flex items-center gap-3">
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs',
                            trade.transaction_type === 'purchase' && 'bg-success/10 text-success border-success/30',
                            trade.transaction_type === 'sale' && 'bg-destructive/10 text-destructive border-destructive/30',
                            trade.transaction_type === 'holding' && 'bg-primary/10 text-primary border-primary/30',
                            !['purchase', 'sale', 'holding'].includes(trade.transaction_type || '') && 'bg-muted/10 text-muted-foreground border-muted'
                          )}
                        >
                          {trade.transaction_type === 'purchase' ? 'BUY' :
                           trade.transaction_type === 'sale' ? 'SELL' :
                           trade.transaction_type === 'holding' ? 'HOLD' :
                           trade.transaction_type?.toUpperCase() || 'N/A'}
                        </Badge>
                        <div>
                          <span className="font-mono font-semibold">
                            {trade.asset_ticker || 'N/A'}
                          </span>
                          <span className="text-muted-foreground ml-2 text-xs">
                            {trade.asset_name?.slice(0, 30)}
                            {(trade.asset_name?.length || 0) > 30 ? '...' : ''}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">
                          {new Date(trade.disclosure_date).toLocaleDateString()}
                        </p>
                        {trade.source_url && (
                          <a
                            href={trade.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                          >
                            Source <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-12 text-center text-muted-foreground">
            No trading data available
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
