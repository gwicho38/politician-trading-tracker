/**
 * DropComposer Component
 * Text input for creating new drops with character limit
 */

import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

interface DropComposerProps {
  onSubmit: (content: string) => void;
  isSubmitting?: boolean;
  maxLength?: number;
  placeholder?: string;
}

const DEFAULT_MAX_LENGTH = 500;
const DEFAULT_PLACEHOLDER = "What's happening in the market? Use $TICKER to mention stocks...";

export function DropComposer({
  onSubmit,
  isSubmitting = false,
  maxLength = DEFAULT_MAX_LENGTH,
  placeholder = DEFAULT_PLACEHOLDER,
}: DropComposerProps) {
  const [content, setContent] = useState('');
  const charCount = content.length;
  const isOverLimit = charCount > maxLength;
  const isNearLimit = charCount > maxLength * 0.9;
  const canSubmit = content.trim().length > 0 && !isOverLimit && !isSubmitting;

  const handleSubmit = () => {
    if (canSubmit) {
      onSubmit(content.trim());
      setContent('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Ctrl/Cmd + Enter
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <Card className="bg-card/60 backdrop-blur-xl">
      <CardContent className="pt-4 pb-3 space-y-3">
        <Textarea
          placeholder={placeholder}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-[100px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
          disabled={isSubmitting}
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'text-sm tabular-nums transition-colors',
                isOverLimit
                  ? 'text-destructive font-medium'
                  : isNearLimit
                  ? 'text-amber-500'
                  : 'text-muted-foreground'
              )}
            >
              {charCount}/{maxLength}
            </span>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              Tip: Use $AAPL to mention tickers
            </span>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            size="sm"
            className="gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Posting...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Drop
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default DropComposer;
