/**
 * Signal Playground Types
 * Types for the interactive signal generation playground feature
 */

/**
 * Signal weight configuration for confidence calculation
 * All weight values are between 0 and 1 (percentages as decimals)
 * Threshold values have custom ranges based on buy/sell ratios
 */
export interface SignalWeights {
  // Base confidence starting point
  baseConfidence: number;

  // Politician count bonuses
  politicianCount5Plus: number;
  politicianCount3_4: number;
  politicianCount2: number;

  // Recent activity bonuses (trades in last 30 days)
  recentActivity5Plus: number;
  recentActivity2_4: number;

  // Bipartisan agreement bonus
  bipartisanBonus: number;

  // Volume magnitude bonuses
  volume1MPlus: number;
  volume100KPlus: number;

  // Signal type bonuses
  strongSignalBonus: number;
  moderateSignalBonus: number;

  // Signal type thresholds (buy/sell ratios)
  strongBuyThreshold: number;
  buyThreshold: number;
  strongSellThreshold: number;
  sellThreshold: number;
}

/**
 * Database-stored weight preset
 */
export interface SignalPreset {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  is_public: boolean;
  author_name?: string | null;

  // Weight values (snake_case to match DB schema)
  base_confidence: number;
  politician_count_5_plus: number;
  politician_count_3_4: number;
  politician_count_2: number;
  recent_activity_5_plus: number;
  recent_activity_2_4: number;
  bipartisan_bonus: number;
  volume_1m_plus: number;
  volume_100k_plus: number;
  strong_signal_bonus: number;
  moderate_signal_bonus: number;
  strong_buy_threshold: number;
  buy_threshold: number;
  strong_sell_threshold: number;
  sell_threshold: number;

  created_at: string;
  updated_at: string;
}

/**
 * Signal type classification
 */
export type SignalType = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

/**
 * Individual preview signal from the API
 * Note: Field names match the API response (snake_case)
 */
export interface PreviewSignal {
  ticker: string;
  signal_type: SignalType;
  confidence_score: number;
  buy_count: number;
  sell_count: number;
  total_transaction_volume: number;
  politician_activity_count: number;
  recent_trades: number;
  bipartisan: boolean;
  buy_sell_ratio: number;
  ml_enhanced?: boolean;
  ml_confidence?: number;
  ml_prediction?: number;
}

/**
 * Statistics returned with preview response
 */
export interface PreviewStats {
  totalDisclosures: number;
  uniqueTickers: number;
  signalsGenerated: number;
  signalTypeDistribution: Record<SignalType, number>;
  mlEnabled?: boolean;
  mlEnhancedCount?: number;
}

/**
 * API response from preview-signals endpoint
 */
export interface PreviewResponse {
  success: boolean;
  preview: boolean;
  signals: PreviewSignal[];
  stats: PreviewStats;
  weights: SignalWeights; // Note: edge function returns 'weights', not 'weightsApplied'
  requestId?: string;
}

/**
 * Weight category for UI grouping
 */
export interface WeightCategory {
  id: string;
  name: string;
  description: string;
  fields: WeightField[];
}

/**
 * Individual weight field configuration for UI
 */
export interface WeightField {
  key: keyof SignalWeights;
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  format: 'percent' | 'ratio';
}

/**
 * Form state for creating/editing presets
 */
export interface PresetFormData {
  name: string;
  description: string;
  is_public: boolean;
  weights: SignalWeights;
}

/**
 * Chart data point for signal distribution
 */
export interface SignalDistributionData {
  name: string;
  value: number;
  fill: string;
}

/**
 * Chart data point for confidence distribution
 */
export interface ConfidenceDistributionData {
  range: string;
  count: number;
}

/**
 * Strategy like record
 */
export interface StrategyLike {
  id: string;
  user_id: string;
  preset_id: string;
  created_at: string;
}

/**
 * Strategy for showcase with likes and author info
 * Returned by get_public_strategies database function
 */
export interface ShowcaseStrategy extends SignalPreset {
  author_name: string | null;
  author_email: string | null;
  likes_count: number;
  user_has_liked: boolean;
}
