/**
 * Tests for lib/signal-weights.ts
 *
 * Tests:
 * - DEFAULT_WEIGHTS - Default weight values
 * - WEIGHT_CATEGORIES - Weight categories configuration
 * - SIGNAL_TYPE_CONFIG - Signal type display configuration
 * - presetToWeights() - Convert database preset to SignalWeights
 * - weightsToPresetFields() - Convert SignalWeights to database format
 * - formatWeightValue() - Format weight for display
 * - formatWeightDiff() - Format weight diff for display
 * - getWeightDiff() - Calculate diff from default
 * - hasChangesFromDefault() - Check if weights modified
 * - countModifiedFields() - Count modified fields
 */

import { describe, it, expect } from 'vitest';
import {
  DEFAULT_WEIGHTS,
  WEIGHT_CATEGORIES,
  SIGNAL_TYPE_CONFIG,
  presetToWeights,
  weightsToPresetFields,
  formatWeightValue,
  formatWeightDiff,
  getWeightDiff,
  hasChangesFromDefault,
  countModifiedFields,
  type SignalPreset,
} from './signal-weights';

describe('DEFAULT_WEIGHTS', () => {
  it('has all required fields', () => {
    expect(DEFAULT_WEIGHTS).toHaveProperty('baseConfidence');
    expect(DEFAULT_WEIGHTS).toHaveProperty('politicianCount5Plus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('politicianCount3_4');
    expect(DEFAULT_WEIGHTS).toHaveProperty('politicianCount2');
    expect(DEFAULT_WEIGHTS).toHaveProperty('recentActivity5Plus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('recentActivity2_4');
    expect(DEFAULT_WEIGHTS).toHaveProperty('bipartisanBonus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('volume1MPlus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('volume100KPlus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('strongSignalBonus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('moderateSignalBonus');
    expect(DEFAULT_WEIGHTS).toHaveProperty('strongBuyThreshold');
    expect(DEFAULT_WEIGHTS).toHaveProperty('buyThreshold');
    expect(DEFAULT_WEIGHTS).toHaveProperty('strongSellThreshold');
    expect(DEFAULT_WEIGHTS).toHaveProperty('sellThreshold');
  });

  it('has baseConfidence of 0.5', () => {
    expect(DEFAULT_WEIGHTS.baseConfidence).toBe(0.5);
  });

  it('has reasonable threshold values', () => {
    expect(DEFAULT_WEIGHTS.strongBuyThreshold).toBeGreaterThan(DEFAULT_WEIGHTS.buyThreshold);
    expect(DEFAULT_WEIGHTS.sellThreshold).toBeGreaterThan(DEFAULT_WEIGHTS.strongSellThreshold);
  });
});

describe('WEIGHT_CATEGORIES', () => {
  it('is an array', () => {
    expect(Array.isArray(WEIGHT_CATEGORIES)).toBe(true);
  });

  it('has base category', () => {
    const baseCategory = WEIGHT_CATEGORIES.find((c) => c.id === 'base');
    expect(baseCategory).toBeDefined();
    expect(baseCategory?.name).toBe('Base Confidence');
  });

  it('has politician-count category', () => {
    const category = WEIGHT_CATEGORIES.find((c) => c.id === 'politician-count');
    expect(category).toBeDefined();
  });

  it('has thresholds category', () => {
    const category = WEIGHT_CATEGORIES.find((c) => c.id === 'thresholds');
    expect(category).toBeDefined();
  });

  it('all categories have required fields', () => {
    WEIGHT_CATEGORIES.forEach((category) => {
      expect(category).toHaveProperty('id');
      expect(category).toHaveProperty('name');
      expect(category).toHaveProperty('description');
      expect(category).toHaveProperty('fields');
      expect(Array.isArray(category.fields)).toBe(true);
    });
  });
});

describe('SIGNAL_TYPE_CONFIG', () => {
  it('has all signal types', () => {
    expect(SIGNAL_TYPE_CONFIG).toHaveProperty('strong_buy');
    expect(SIGNAL_TYPE_CONFIG).toHaveProperty('buy');
    expect(SIGNAL_TYPE_CONFIG).toHaveProperty('hold');
    expect(SIGNAL_TYPE_CONFIG).toHaveProperty('sell');
    expect(SIGNAL_TYPE_CONFIG).toHaveProperty('strong_sell');
  });

  it('each type has label, color, bgColor', () => {
    Object.values(SIGNAL_TYPE_CONFIG).forEach((config) => {
      expect(config).toHaveProperty('label');
      expect(config).toHaveProperty('color');
      expect(config).toHaveProperty('bgColor');
    });
  });

  it('strong_buy has label "Strong Buy"', () => {
    expect(SIGNAL_TYPE_CONFIG.strong_buy.label).toBe('Strong Buy');
  });

  it('hold has label "Hold"', () => {
    expect(SIGNAL_TYPE_CONFIG.hold.label).toBe('Hold');
  });
});

describe('presetToWeights()', () => {
  it('converts database preset to SignalWeights', () => {
    const preset = {
      id: '123',
      user_id: 'user-1',
      name: 'Test Preset',
      description: 'Test',
      is_public: false,
      base_confidence: '0.6',
      politician_count_5_plus: '0.2',
      politician_count_3_4: '0.15',
      politician_count_2: '0.1',
      recent_activity_5_plus: '0.15',
      recent_activity_2_4: '0.1',
      bipartisan_bonus: '0.15',
      volume_1m_plus: '0.15',
      volume_100k_plus: '0.1',
      strong_signal_bonus: '0.2',
      moderate_signal_bonus: '0.15',
      strong_buy_threshold: '3.5',
      buy_threshold: '2.5',
      strong_sell_threshold: '0.3',
      sell_threshold: '0.4',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    };

    const weights = presetToWeights(preset as SignalPreset);

    expect(weights.baseConfidence).toBe(0.6);
    expect(weights.politicianCount5Plus).toBe(0.2);
    expect(weights.strongBuyThreshold).toBe(3.5);
  });

  it('handles numeric strings', () => {
    const preset = {
      base_confidence: '0.55',
      politician_count_5_plus: '0.18',
      politician_count_3_4: '0.12',
      politician_count_2: '0.07',
      recent_activity_5_plus: '0.12',
      recent_activity_2_4: '0.07',
      bipartisan_bonus: '0.12',
      volume_1m_plus: '0.12',
      volume_100k_plus: '0.07',
      strong_signal_bonus: '0.18',
      moderate_signal_bonus: '0.12',
      strong_buy_threshold: '3.2',
      buy_threshold: '2.2',
      strong_sell_threshold: '0.35',
      sell_threshold: '0.55',
    };

    const weights = presetToWeights(preset as SignalPreset);

    expect(weights.baseConfidence).toBe(0.55);
  });
});

describe('weightsToPresetFields()', () => {
  it('converts SignalWeights to database format', () => {
    const weights = { ...DEFAULT_WEIGHTS };
    const fields = weightsToPresetFields(weights);

    expect(fields.base_confidence).toBe(0.5);
    expect(fields.politician_count_5_plus).toBe(0.15);
    expect(fields.strong_buy_threshold).toBe(3.0);
  });

  it('uses snake_case keys', () => {
    const fields = weightsToPresetFields(DEFAULT_WEIGHTS);

    expect(fields).toHaveProperty('base_confidence');
    expect(fields).toHaveProperty('politician_count_5_plus');
    expect(fields).toHaveProperty('recent_activity_5_plus');
    expect(fields).not.toHaveProperty('baseConfidence');
  });
});

describe('formatWeightValue()', () => {
  it('formats percent values', () => {
    expect(formatWeightValue(0.5, 'percent')).toBe('50%');
    expect(formatWeightValue(0.15, 'percent')).toBe('15%');
    expect(formatWeightValue(1, 'percent')).toBe('100%');
  });

  it('formats ratio values', () => {
    expect(formatWeightValue(3, 'ratio')).toBe('3.00x');
    expect(formatWeightValue(2.5, 'ratio')).toBe('2.50x');
    expect(formatWeightValue(0.33, 'ratio')).toBe('0.33x');
  });
});

describe('formatWeightDiff()', () => {
  it('formats positive percent diff', () => {
    expect(formatWeightDiff(0.1, 'percent')).toBe('+10');
  });

  it('formats negative percent diff', () => {
    expect(formatWeightDiff(-0.15, 'percent')).toBe('-15');
  });

  it('formats zero diff', () => {
    expect(formatWeightDiff(0, 'percent')).toBe('0');
  });

  it('formats positive ratio diff', () => {
    expect(formatWeightDiff(0.5, 'ratio')).toBe('+0.50');
  });

  it('formats negative ratio diff', () => {
    expect(formatWeightDiff(-0.25, 'ratio')).toBe('-0.25');
  });
});

describe('getWeightDiff()', () => {
  it('returns 0 when weight equals default', () => {
    const diff = getWeightDiff(DEFAULT_WEIGHTS, 'baseConfidence');
    expect(diff).toBe(0);
  });

  it('returns positive diff when weight is higher', () => {
    const weights = { ...DEFAULT_WEIGHTS, baseConfidence: 0.7 };
    const diff = getWeightDiff(weights, 'baseConfidence');
    expect(diff).toBeCloseTo(0.2);
  });

  it('returns negative diff when weight is lower', () => {
    const weights = { ...DEFAULT_WEIGHTS, baseConfidence: 0.3 };
    const diff = getWeightDiff(weights, 'baseConfidence');
    expect(diff).toBeCloseTo(-0.2);
  });
});

describe('hasChangesFromDefault()', () => {
  it('returns false for default weights', () => {
    expect(hasChangesFromDefault(DEFAULT_WEIGHTS)).toBe(false);
  });

  it('returns true when any weight is modified', () => {
    const weights = { ...DEFAULT_WEIGHTS, baseConfidence: 0.6 };
    expect(hasChangesFromDefault(weights)).toBe(true);
  });

  it('returns true for multiple modifications', () => {
    const weights = {
      ...DEFAULT_WEIGHTS,
      baseConfidence: 0.6,
      politicianCount5Plus: 0.2,
    };
    expect(hasChangesFromDefault(weights)).toBe(true);
  });
});

describe('countModifiedFields()', () => {
  it('returns 0 for default weights', () => {
    expect(countModifiedFields(DEFAULT_WEIGHTS)).toBe(0);
  });

  it('returns 1 for single modification', () => {
    const weights = { ...DEFAULT_WEIGHTS, baseConfidence: 0.6 };
    expect(countModifiedFields(weights)).toBe(1);
  });

  it('returns correct count for multiple modifications', () => {
    const weights = {
      ...DEFAULT_WEIGHTS,
      baseConfidence: 0.6,
      politicianCount5Plus: 0.2,
      bipartisanBonus: 0.15,
    };
    expect(countModifiedFields(weights)).toBe(3);
  });
});
