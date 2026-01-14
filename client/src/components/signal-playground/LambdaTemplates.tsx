/**
 * LambdaTemplates Component
 * Library of pre-built lambda templates for signal transformation
 */

import { useState } from 'react';
import { BookOpen, Zap, Filter, Calculator, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

type TemplateCategory = 'confidence' | 'signal_type' | 'filtering' | 'math';

interface LambdaTemplate {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  code: string;
}

const CATEGORY_INFO: Record<TemplateCategory, { icon: typeof Zap; label: string }> = {
  confidence: { icon: TrendingUp, label: 'Confidence' },
  signal_type: { icon: Zap, label: 'Signal Type' },
  filtering: { icon: Filter, label: 'Filtering' },
  math: { icon: Calculator, label: 'Math' },
};

const LAMBDA_TEMPLATES: LambdaTemplate[] = [
  // Confidence adjustments
  {
    id: 'boost-high-ratio',
    name: 'Boost High Buy/Sell Ratio',
    description: 'Increase confidence for signals with strong buy/sell ratios',
    category: 'confidence',
    code: `# Boost confidence when buy/sell ratio is very high
if signal.get("buy_sell_ratio", 0) > 2.0:
    boost = min(0.15, signal["buy_sell_ratio"] * 0.05)
    signal["confidence_score"] = min(signal["confidence_score"] + boost, 0.99)
result = signal`,
  },
  {
    id: 'penalize-low-activity',
    name: 'Penalize Low Politician Count',
    description: 'Reduce confidence when fewer politicians are trading',
    category: 'confidence',
    code: `# Reduce confidence for signals with low politician count
count = signal.get("politician_activity_count", 0)
if count < 3:
    penalty = (3 - count) * 0.1
    signal["confidence_score"] = max(signal["confidence_score"] - penalty, 0.1)
result = signal`,
  },
  {
    id: 'volume-boost',
    name: 'Volume-Based Confidence Boost',
    description: 'Increase confidence based on transaction volume',
    category: 'confidence',
    code: `# Boost confidence based on volume
volume = signal.get("total_transaction_volume", 0)
if volume > 1000000:
    signal["confidence_score"] = min(signal["confidence_score"] + 0.15, 0.99)
elif volume > 100000:
    signal["confidence_score"] = min(signal["confidence_score"] + 0.08, 0.95)
result = signal`,
  },
  {
    id: 'bipartisan-boost',
    name: 'Bipartisan Agreement Boost',
    description: 'Significantly boost confidence for bipartisan signals',
    category: 'confidence',
    code: `# Strong boost for bipartisan agreement
if signal.get("bipartisan", False):
    signal["confidence_score"] = min(signal["confidence_score"] + 0.20, 0.99)
result = signal`,
  },

  // Signal type changes
  {
    id: 'weak-to-hold',
    name: 'Convert Weak Signals to Hold',
    description: 'Change weak buy/sell signals to hold',
    category: 'signal_type',
    code: `# Convert weak signals to hold
confidence = signal.get("confidence_score", 0)
signal_type = signal.get("signal_type", "hold")

if signal_type in ["buy", "sell"] and confidence < 0.4:
    signal["signal_type"] = "hold"
result = signal`,
  },
  {
    id: 'strong-only',
    name: 'Keep Only Strong Signals',
    description: 'Convert non-strong signals to hold',
    category: 'signal_type',
    code: `# Only keep strong_buy and strong_sell signals
signal_type = signal.get("signal_type", "hold")
if signal_type not in ["strong_buy", "strong_sell"]:
    signal["signal_type"] = "hold"
result = signal`,
  },
  {
    id: 'promote-to-strong',
    name: 'Promote High Confidence to Strong',
    description: 'Upgrade signals with high confidence to strong versions',
    category: 'signal_type',
    code: `# Promote high confidence signals to strong
confidence = signal.get("confidence_score", 0)
signal_type = signal.get("signal_type", "hold")

if confidence > 0.85:
    if signal_type == "buy":
        signal["signal_type"] = "strong_buy"
    elif signal_type == "sell":
        signal["signal_type"] = "strong_sell"
result = signal`,
  },

  // Filtering
  {
    id: 'bipartisan-only',
    name: 'Require Bipartisan Support',
    description: 'Only show signals with bipartisan agreement',
    category: 'filtering',
    code: `# Filter to only bipartisan signals
if not signal.get("bipartisan", False):
    signal["confidence_score"] = 0
    signal["signal_type"] = "hold"
result = signal`,
  },
  {
    id: 'min-politicians',
    name: 'Minimum Politician Threshold',
    description: 'Require at least 3 politicians for signal consideration',
    category: 'filtering',
    code: `# Require minimum politician count
if signal.get("politician_activity_count", 0) < 3:
    signal["confidence_score"] = 0
    signal["signal_type"] = "hold"
result = signal`,
  },
  {
    id: 'recent-only',
    name: 'Require Recent Activity',
    description: 'Filter signals without recent trading activity',
    category: 'filtering',
    code: `# Require recent trades for validity
if signal.get("recent_trades", 0) < 2:
    signal["confidence_score"] = signal["confidence_score"] * 0.5
result = signal`,
  },

  // Math operations
  {
    id: 'log-scale',
    name: 'Logarithmic Confidence Scaling',
    description: 'Apply logarithmic scaling to confidence scores',
    category: 'math',
    code: `# Logarithmic scaling for smoother distribution
conf = signal.get("confidence_score", 0.5)
if conf > 0:
    # log1p for numerical stability
    signal["confidence_score"] = math.log1p(conf * 10) / math.log1p(10)
result = signal`,
  },
  {
    id: 'sqrt-scale',
    name: 'Square Root Scaling',
    description: 'Apply square root scaling to boost low confidence signals',
    category: 'math',
    code: `# Square root scaling boosts lower values
conf = signal.get("confidence_score", 0.5)
signal["confidence_score"] = math.sqrt(conf)
result = signal`,
  },
  {
    id: 'weighted-average',
    name: 'Weighted Score Calculation',
    description: 'Calculate custom weighted score from multiple factors',
    category: 'math',
    code: `# Custom weighted score from multiple factors
ratio_weight = 0.3
count_weight = 0.3
volume_weight = 0.2
recent_weight = 0.2

ratio_score = min(signal.get("buy_sell_ratio", 1) / 3.0, 1.0)
count_score = min(signal.get("politician_activity_count", 0) / 5.0, 1.0)
volume_score = min(signal.get("total_transaction_volume", 0) / 1000000, 1.0)
recent_score = min(signal.get("recent_trades", 0) / 5.0, 1.0)

weighted = (ratio_score * ratio_weight + count_score * count_weight +
            volume_score * volume_weight + recent_score * recent_weight)
signal["confidence_score"] = weighted
result = signal`,
  },
];

interface LambdaTemplatesProps {
  onSelect: (code: string) => void;
}

export function LambdaTemplates({ onSelect }: LambdaTemplatesProps) {
  const [open, setOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<TemplateCategory>('confidence');

  const handleSelect = (template: LambdaTemplate) => {
    onSelect(template.code);
    setOpen(false);
  };

  const templatesByCategory = LAMBDA_TEMPLATES.reduce(
    (acc, template) => {
      if (!acc[template.category]) {
        acc[template.category] = [];
      }
      acc[template.category].push(template);
      return acc;
    },
    {} as Record<TemplateCategory, LambdaTemplate[]>
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <BookOpen className="h-4 w-4" />
          Templates
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Tabs
          value={activeCategory}
          onValueChange={(v) => setActiveCategory(v as TemplateCategory)}
          className="w-full"
        >
          <div className="border-b px-3 pt-3">
            <h4 className="font-medium text-sm mb-2">Lambda Templates</h4>
            <TabsList className="w-full justify-start h-8 bg-transparent p-0 gap-1">
              {(Object.keys(CATEGORY_INFO) as TemplateCategory[]).map((category) => {
                const { icon: Icon, label } = CATEGORY_INFO[category];
                return (
                  <TabsTrigger
                    key={category}
                    value={category}
                    className="text-xs data-[state=active]:bg-secondary px-2 py-1"
                  >
                    <Icon className="h-3 w-3 mr-1" />
                    {label}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

          <ScrollArea className="h-[300px]">
            {(Object.keys(CATEGORY_INFO) as TemplateCategory[]).map((category) => (
              <TabsContent key={category} value={category} className="m-0 p-2">
                <div className="space-y-2">
                  {templatesByCategory[category]?.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => handleSelect(template)}
                      className="w-full text-left p-3 rounded-md border hover:bg-secondary/50 transition-colors"
                    >
                      <div className="font-medium text-sm">{template.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {template.description}
                      </div>
                    </button>
                  ))}
                </div>
              </TabsContent>
            ))}
          </ScrollArea>
        </Tabs>
      </PopoverContent>
    </Popover>
  );
}

export default LambdaTemplates;
