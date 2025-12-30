/**
 * Signal Weights Utilities
 * Default values and UI category definitions for the signal playground
 */

import type {
  SignalWeights,
  SignalPreset,
  WeightCategory,
  SignalType,
} from '@/types/signal-playground';

/**
 * Default weight values matching the edge function defaults
 */
export const DEFAULT_WEIGHTS: SignalWeights = {
  baseConfidence: 0.5,
  politicianCount5Plus: 0.15,
  politicianCount3_4: 0.1,
  politicianCount2: 0.05,
  recentActivity5Plus: 0.1,
  recentActivity2_4: 0.05,
  bipartisanBonus: 0.1,
  volume1MPlus: 0.1,
  volume100KPlus: 0.05,
  strongSignalBonus: 0.15,
  moderateSignalBonus: 0.1,
  strongBuyThreshold: 3.0,
  buyThreshold: 2.0,
  strongSellThreshold: 0.33,
  sellThreshold: 0.5,
};

/**
 * Weight categories for organized UI display
 */
export const WEIGHT_CATEGORIES: WeightCategory[] = [
  {
    id: 'base',
    name: 'Base Confidence',
    description: 'Starting confidence level before bonuses',
    fields: [
      {
        key: 'baseConfidence',
        label: 'Base Confidence',
        description: 'Initial confidence score (0.3-0.7 recommended)',
        min: 0,
        max: 1,
        step: 0.05,
        format: 'percent',
      },
    ],
  },
  {
    id: 'politician-count',
    name: 'Politician Count',
    description: 'Bonus based on number of politicians trading the ticker',
    fields: [
      {
        key: 'politicianCount5Plus',
        label: '5+ Politicians',
        description: 'Bonus when 5 or more politicians are trading',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
      {
        key: 'politicianCount3_4',
        label: '3-4 Politicians',
        description: 'Bonus when 3-4 politicians are trading',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
      {
        key: 'politicianCount2',
        label: '2 Politicians',
        description: 'Bonus when 2 politicians are trading',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
    ],
  },
  {
    id: 'recent-activity',
    name: 'Recent Activity',
    description: 'Bonus based on trades in the last 30 days',
    fields: [
      {
        key: 'recentActivity5Plus',
        label: '5+ Recent Trades',
        description: 'Bonus when 5+ trades in last 30 days',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
      {
        key: 'recentActivity2_4',
        label: '2-4 Recent Trades',
        description: 'Bonus when 2-4 trades in last 30 days',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
    ],
  },
  {
    id: 'bipartisan',
    name: 'Bipartisan Agreement',
    description: 'Bonus when both parties are trading the same direction',
    fields: [
      {
        key: 'bipartisanBonus',
        label: 'Bipartisan Bonus',
        description: 'Bonus when Democrats and Republicans agree',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
    ],
  },
  {
    id: 'volume',
    name: 'Trading Volume',
    description: 'Bonus based on total trading volume',
    fields: [
      {
        key: 'volume1MPlus',
        label: '$1M+ Volume',
        description: 'Bonus when total volume exceeds $1M',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
      {
        key: 'volume100KPlus',
        label: '$100K+ Volume',
        description: 'Bonus when total volume exceeds $100K',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
    ],
  },
  {
    id: 'signal-bonuses',
    name: 'Signal Strength Bonuses',
    description: 'Additional confidence for strong/moderate signals',
    fields: [
      {
        key: 'strongSignalBonus',
        label: 'Strong Signal Bonus',
        description: 'Extra confidence for strong buy/sell signals',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
      {
        key: 'moderateSignalBonus',
        label: 'Moderate Signal Bonus',
        description: 'Extra confidence for moderate buy/sell signals',
        min: 0,
        max: 0.5,
        step: 0.01,
        format: 'percent',
      },
    ],
  },
  {
    id: 'thresholds',
    name: 'Signal Thresholds',
    description: 'Buy/sell ratio thresholds for signal classification',
    fields: [
      {
        key: 'strongBuyThreshold',
        label: 'Strong Buy Threshold',
        description: 'Buy/sell ratio above this = strong buy (default 3:1)',
        min: 1.5,
        max: 5,
        step: 0.1,
        format: 'ratio',
      },
      {
        key: 'buyThreshold',
        label: 'Buy Threshold',
        description: 'Buy/sell ratio above this = buy (default 2:1)',
        min: 1,
        max: 4,
        step: 0.1,
        format: 'ratio',
      },
      {
        key: 'sellThreshold',
        label: 'Sell Threshold',
        description: 'Buy/sell ratio below this = sell (default 0.5)',
        min: 0.1,
        max: 1,
        step: 0.05,
        format: 'ratio',
      },
      {
        key: 'strongSellThreshold',
        label: 'Strong Sell Threshold',
        description: 'Buy/sell ratio below this = strong sell (default 0.33)',
        min: 0.1,
        max: 0.9,
        step: 0.05,
        format: 'ratio',
      },
    ],
  },
];

/**
 * Signal type display configuration
 */
export const SIGNAL_TYPE_CONFIG: Record<
  SignalType,
  { label: string; color: string; bgColor: string }
> = {
  strong_buy: {
    label: 'Strong Buy',
    color: 'hsl(142, 76%, 36%)',
    bgColor: 'hsl(142, 76%, 36%, 0.1)',
  },
  buy: {
    label: 'Buy',
    color: 'hsl(142, 60%, 50%)',
    bgColor: 'hsl(142, 60%, 50%, 0.1)',
  },
  hold: {
    label: 'Hold',
    color: 'hsl(45, 93%, 47%)',
    bgColor: 'hsl(45, 93%, 47%, 0.1)',
  },
  sell: {
    label: 'Sell',
    color: 'hsl(0, 60%, 50%)',
    bgColor: 'hsl(0, 60%, 50%, 0.1)',
  },
  strong_sell: {
    label: 'Strong Sell',
    color: 'hsl(0, 84%, 60%)',
    bgColor: 'hsl(0, 84%, 60%, 0.1)',
  },
};

/**
 * Convert database preset to SignalWeights
 */
export function presetToWeights(preset: SignalPreset): SignalWeights {
  return {
    baseConfidence: Number(preset.base_confidence),
    politicianCount5Plus: Number(preset.politician_count_5_plus),
    politicianCount3_4: Number(preset.politician_count_3_4),
    politicianCount2: Number(preset.politician_count_2),
    recentActivity5Plus: Number(preset.recent_activity_5_plus),
    recentActivity2_4: Number(preset.recent_activity_2_4),
    bipartisanBonus: Number(preset.bipartisan_bonus),
    volume1MPlus: Number(preset.volume_1m_plus),
    volume100KPlus: Number(preset.volume_100k_plus),
    strongSignalBonus: Number(preset.strong_signal_bonus),
    moderateSignalBonus: Number(preset.moderate_signal_bonus),
    strongBuyThreshold: Number(preset.strong_buy_threshold),
    buyThreshold: Number(preset.buy_threshold),
    strongSellThreshold: Number(preset.strong_sell_threshold),
    sellThreshold: Number(preset.sell_threshold),
  };
}

/**
 * Convert SignalWeights to database format (snake_case)
 */
export function weightsToPresetFields(
  weights: SignalWeights
): Omit<SignalPreset, 'id' | 'user_id' | 'name' | 'description' | 'is_public' | 'created_at' | 'updated_at'> {
  return {
    base_confidence: weights.baseConfidence,
    politician_count_5_plus: weights.politicianCount5Plus,
    politician_count_3_4: weights.politicianCount3_4,
    politician_count_2: weights.politicianCount2,
    recent_activity_5_plus: weights.recentActivity5Plus,
    recent_activity_2_4: weights.recentActivity2_4,
    bipartisan_bonus: weights.bipartisanBonus,
    volume_1m_plus: weights.volume1MPlus,
    volume_100k_plus: weights.volume100KPlus,
    strong_signal_bonus: weights.strongSignalBonus,
    moderate_signal_bonus: weights.moderateSignalBonus,
    strong_buy_threshold: weights.strongBuyThreshold,
    buy_threshold: weights.buyThreshold,
    strong_sell_threshold: weights.strongSellThreshold,
    sell_threshold: weights.sellThreshold,
  };
}

/**
 * Format weight value for display
 */
export function formatWeightValue(value: number, format: 'percent' | 'ratio'): string {
  if (format === 'percent') {
    return `${Math.round(value * 100)}%`;
  }
  return `${value.toFixed(2)}x`;
}

/**
 * Format weight diff for display (used in badges to show change from default)
 * Uses a clearer format to avoid confusion with the main value
 */
export function formatWeightDiff(diff: number, format: 'percent' | 'ratio'): string {
  if (format === 'percent') {
    // Show percentage point change without % to avoid confusion
    // e.g., +32 instead of +32% when value went from 10% to 42%
    const points = Math.round(diff * 100);
    return `${points > 0 ? '+' : ''}${points}`;
  }
  // For ratios, show the decimal diff
  return `${diff > 0 ? '+' : ''}${diff.toFixed(2)}`;
}

/**
 * Calculate diff from default weights
 */
export function getWeightDiff(
  weights: SignalWeights,
  key: keyof SignalWeights
): number {
  return weights[key] - DEFAULT_WEIGHTS[key];
}

/**
 * Check if weights have been modified from defaults
 */
export function hasChangesFromDefault(weights: SignalWeights): boolean {
  return Object.keys(DEFAULT_WEIGHTS).some(
    (key) => weights[key as keyof SignalWeights] !== DEFAULT_WEIGHTS[key as keyof SignalWeights]
  );
}

/**
 * Count number of modified fields from defaults
 */
export function countModifiedFields(weights: SignalWeights): number {
  return Object.keys(DEFAULT_WEIGHTS).filter(
    (key) => weights[key as keyof SignalWeights] !== DEFAULT_WEIGHTS[key as keyof SignalWeights]
  ).length;
}
