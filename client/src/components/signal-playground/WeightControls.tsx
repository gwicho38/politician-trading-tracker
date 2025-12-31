/**
 * WeightControls Component
 * Left panel with accordion sections for adjusting signal weights
 */

import { RotateCcw, Save, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  WEIGHT_CATEGORIES,
  DEFAULT_WEIGHTS,
  formatWeightValue,
  formatWeightDiff,
} from '@/lib/signal-weights';
import type { SignalWeights, WeightField } from '@/types/signal-playground';

interface WeightControlsProps {
  weights: SignalWeights;
  onWeightChange: <K extends keyof SignalWeights>(
    key: K,
    value: SignalWeights[K]
  ) => void;
  onReset: () => void;
  onSave: () => void;
  hasChanges: boolean;
  modifiedCount: number;
  isUpdating?: boolean;
  canSave?: boolean; // Whether user is logged in and can save presets
}

/**
 * Individual weight slider with label and value display
 */
function WeightSlider({
  field,
  value,
  onChange,
}: {
  field: WeightField;
  value: number;
  onChange: (value: number) => void;
}) {
  const defaultValue = DEFAULT_WEIGHTS[field.key];
  const diff = value - defaultValue;
  const hasDiff = Math.abs(diff) > 0.001;

  return (
    <div className="space-y-2 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium">
            {field.label}
          </span>
          <Tooltip>
            <TooltipTrigger asChild>
              <HelpCircle className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground cursor-help transition-colors" />
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              <p>{field.description}</p>
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="flex items-center gap-2">
          {hasDiff && (
            <Badge
              variant={diff > 0 ? 'default' : 'secondary'}
              className="text-xs px-1.5 py-0"
            >
              {formatWeightDiff(diff, field.format)}
            </Badge>
          )}
          <span className="text-sm font-mono w-14 text-right">
            {formatWeightValue(value, field.format)}
          </span>
        </div>
      </div>

      <Slider
        value={[value]}
        min={field.min}
        max={field.max}
        step={field.step}
        onValueChange={([newValue]) => onChange(newValue)}
        className="cursor-pointer"
      />
    </div>
  );
}

export function WeightControls({
  weights,
  onWeightChange,
  onReset,
  onSave,
  hasChanges,
  modifiedCount,
  isUpdating,
  canSave = true,
}: WeightControlsProps) {
  // Default open the first two categories
  const defaultOpen = WEIGHT_CATEGORIES.slice(0, 2).map((c) => c.id);

  return (
    <div className="flex flex-col h-full">
      {/* Header with action buttons */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">Weight Controls</h3>
          {modifiedCount > 0 && (
            <Badge variant="outline" className="text-xs">
              {modifiedCount} modified
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onReset}
                disabled={!hasChanges}
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reset to defaults</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onSave}
                  disabled={!canSave || isUpdating}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Preset
                </Button>
              </span>
            </TooltipTrigger>
            {!canSave && (
              <TooltipContent>Sign in to save presets</TooltipContent>
            )}
          </Tooltip>
        </div>
      </div>

      {/* Scrollable accordion content */}
      <div className="flex-1 overflow-y-auto p-4">
        <Accordion type="multiple" defaultValue={defaultOpen} className="space-y-2">
          {WEIGHT_CATEGORIES.map((category) => (
            <AccordionItem
              key={category.id}
              value={category.id}
              className="border rounded-lg px-3"
            >
              <AccordionTrigger className="hover:no-underline py-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{category.name}</span>
                  <CategoryDiffBadge
                    category={category}
                    weights={weights}
                  />
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <p className="text-xs text-muted-foreground mb-3">
                  {category.description}
                </p>
                <div className="space-y-1">
                  {category.fields.map((field) => (
                    <WeightSlider
                      key={field.key}
                      field={field}
                      value={weights[field.key]}
                      onChange={(value) => onWeightChange(field.key, value)}
                    />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  );
}

/**
 * Badge showing how many fields in a category are modified
 */
function CategoryDiffBadge({
  category,
  weights,
}: {
  category: (typeof WEIGHT_CATEGORIES)[0];
  weights: SignalWeights;
}) {
  const modifiedInCategory = category.fields.filter(
    (field) =>
      Math.abs(weights[field.key] - DEFAULT_WEIGHTS[field.key]) > 0.001
  ).length;

  if (modifiedInCategory === 0) return null;

  return (
    <Badge variant="secondary" className="text-xs px-1.5 py-0">
      {modifiedInCategory}
    </Badge>
  );
}

export default WeightControls;
