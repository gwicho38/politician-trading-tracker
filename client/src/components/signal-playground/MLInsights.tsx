/**
 * MLInsights Component
 * Displays ML model performance metrics, feature importance, and prediction stats
 * Collapsible panel that can be expanded/collapsed at any time
 */

import { useState, useEffect } from 'react';
import { Brain, BarChart3, Sparkles, RefreshCw, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchWithRetry } from '@/lib/fetchWithRetry';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface ModelInfo {
  id: string;
  model_name: string;
  model_version: string;
  model_type: string;
  status: string;
  metrics: {
    accuracy: number;
    f1_weighted: number;
    training_samples: number;
    validation_samples: number;
  };
  feature_importance: Record<string, number>;
  training_completed_at: string;
}

interface MLInsightsProps {
  mlEnhancedCount?: number;
  totalSignals?: number;
}

const PHOENIX_API_URL = import.meta.env.VITE_PHOENIX_API_URL || 'https://politician-trading-server.fly.dev';

// Feature name mappings for display
const FEATURE_LABELS: Record<string, string> = {
  politician_count: 'Politician Count',
  buy_sell_ratio: 'Buy/Sell Ratio',
  recent_activity_30d: 'Recent Activity',
  bipartisan: 'Bipartisan Agreement',
  net_volume: 'Net Volume',
  volume_magnitude: 'Volume Magnitude',
  party_alignment: 'Party Alignment',
  committee_relevance: 'Committee Relevance',
  disclosure_delay: 'Disclosure Delay',
  sentiment_score: 'Sentiment Score',
  market_momentum: 'Market Momentum',
  sector_performance: 'Sector Performance',
};

// Colors for feature importance bars
const FEATURE_COLORS = [
  'hsl(142, 76%, 36%)', // Green
  'hsl(200, 98%, 39%)', // Blue
  'hsl(262, 83%, 58%)', // Purple
  'hsl(45, 93%, 47%)',  // Yellow
  'hsl(0, 72%, 51%)',   // Red
  'hsl(173, 80%, 40%)', // Cyan
];

export function MLInsights({ mlEnhancedCount, totalSignals }: MLInsightsProps) {
  const [activeModel, setActiveModel] = useState<ModelInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false); // Start collapsed by default

  // ML is always enabled - fetch model on mount
  useEffect(() => {
    fetchActiveModel();
  }, []);

  const fetchActiveModel = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchWithRetry(`${PHOENIX_API_URL}/api/ml/models/active`, {
        maxRetries: 3,
        onRetry: (attempt, err, delay) => {
          console.log(`[MLInsights] Retry ${attempt} after ${delay}ms: ${err.message}`);
        },
      });

      if (response.status === 404) {
        setActiveModel(null);
        setError('No active ML model. Train a model first.');
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch model: ${response.status}`);
      }

      const data = await response.json();
      setActiveModel(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ML model info');
    } finally {
      setIsLoading(false);
    }
  };

  // Prepare feature importance data for chart
  const featureImportanceData = activeModel?.feature_importance
    ? Object.entries(activeModel.feature_importance)
        .map(([key, value]) => ({
          name: FEATURE_LABELS[key] || key,
          value: Math.round((value as number) * 100) / 100,
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 8) // Top 8 features
    : [];

  // Calculate ML enhancement rate
  const mlEnhancementRate = totalSignals && mlEnhancedCount
    ? Math.round((mlEnhancedCount / totalSignals) * 100)
    : 0;

  // Collapsed header component (shared between states)
  const CollapsedHeader = () => (
    <CollapsibleTrigger asChild>
      <div className="flex items-center justify-between cursor-pointer hover:bg-secondary/50 p-3 rounded-lg transition-colors">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4" />
          <span className="text-sm font-medium">ML Insights</span>
          {activeModel && !error && (
            <Badge variant="outline" className="text-xs">
              {activeModel.model_name}
            </Badge>
          )}
          {error && (
            <Badge variant="destructive" className="text-xs">
              No Model
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {totalSignals !== undefined && totalSignals > 0 && (
            <span className="text-xs text-muted-foreground">
              {mlEnhancedCount}/{totalSignals} enhanced
            </span>
          )}
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>
    </CollapsibleTrigger>
  );

  if (isLoading) {
    return (
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <Card>
          <CollapsedHeader />
          <CollapsibleContent>
            <CardContent className="space-y-4 pt-0">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-40 w-full" />
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    );
  }

  if (error) {
    return (
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <Card className="border-destructive/50">
          <CollapsedHeader />
          <CollapsibleContent>
            <CardContent className="pt-0">
              <div className="text-sm text-destructive mb-3">{error}</div>
              <Button variant="outline" size="sm" onClick={fetchActiveModel}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    );
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card>
        <CollapsedHeader />
        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            {/* ML Status Section */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="default" className="bg-emerald-600">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Active
                </Badge>
                {activeModel && (
                  <span className="text-xs text-muted-foreground">
                    v{activeModel.model_version}
                  </span>
                )}
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-4">
              {/* Model Accuracy */}
              {activeModel?.metrics?.accuracy && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Accuracy</div>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={activeModel.metrics.accuracy * 100}
                      className="h-2"
                    />
                    <span className="text-sm font-medium">
                      {Math.round(activeModel.metrics.accuracy * 100)}%
                    </span>
                  </div>
                </div>
              )}

              {/* F1 Score */}
              {activeModel?.metrics?.f1_weighted && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">F1 Score</div>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={activeModel.metrics.f1_weighted * 100}
                      className="h-2"
                    />
                    <span className="text-sm font-medium">
                      {Math.round(activeModel.metrics.f1_weighted * 100)}%
                    </span>
                  </div>
                </div>
              )}

              {/* ML Enhancement Rate */}
              {totalSignals !== undefined && totalSignals > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Enhanced Signals</div>
                  <div className="flex items-center gap-2">
                    <Progress value={mlEnhancementRate} className="h-2" />
                    <span className="text-sm font-medium">
                      {mlEnhancedCount}/{totalSignals}
                    </span>
                  </div>
                </div>
              )}

              {/* Training Samples */}
              {activeModel?.metrics?.training_samples && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Training Samples</div>
                  <div className="text-sm font-medium">
                    {activeModel.metrics.training_samples.toLocaleString()}
                  </div>
                </div>
              )}
            </div>

            {/* Feature Importance Chart */}
            {featureImportanceData.length > 0 && (
              <div className="pt-2 border-t">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="h-4 w-4" />
                  <span className="text-sm font-medium">Feature Importance</span>
                </div>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={featureImportanceData}
                      layout="vertical"
                      margin={{ top: 5, right: 20, left: 80, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" domain={[0, 'auto']} tickFormatter={(v) => v.toFixed(2)} />
                      <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} />
                      <Tooltip
                        formatter={(value: number) => [value.toFixed(4), 'Importance']}
                        labelFormatter={(label) => `Feature: ${label}`}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {featureImportanceData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={FEATURE_COLORS[index % FEATURE_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

export default MLInsights;
