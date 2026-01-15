/**
 * DropComposer Component
 * Text input for creating new drops with character limit and $TICKER autocomplete
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, TrendingUp } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useTickerSearch } from '@/hooks/useTickerSearch';

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
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteQuery, setAutocompleteQuery] = useState('');
  const [autocompleteIndex, setAutocompleteIndex] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autocompleteRef = useRef<HTMLDivElement>(null);

  const charCount = content.length;
  const isOverLimit = charCount > maxLength;
  const isNearLimit = charCount > maxLength * 0.9;
  const canSubmit = content.trim().length > 0 && !isOverLimit && !isSubmitting;

  // Ticker search
  const { data: tickerResults = [], isLoading: isSearching } = useTickerSearch(
    autocompleteQuery,
    showAutocomplete && autocompleteQuery.length >= 1
  );

  // Find the $ trigger position and extract query
  const findTickerContext = useCallback((text: string, cursor: number) => {
    // Look backwards from cursor to find $
    let dollarPos = -1;
    for (let i = cursor - 1; i >= 0; i--) {
      const char = text[i];
      if (char === '$') {
        dollarPos = i;
        break;
      }
      // Stop if we hit whitespace or special chars before finding $
      if (/[\s\n]/.test(char)) {
        break;
      }
    }

    if (dollarPos === -1) return null;

    // Extract the query after $
    const query = text.slice(dollarPos + 1, cursor);

    // Only show autocomplete if query is valid (uppercase letters only)
    if (query.length > 0 && !/^[A-Za-z]*$/.test(query)) {
      return null;
    }

    return { dollarPos, query: query.toUpperCase() };
  }, []);

  // Handle content change
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    const newCursor = e.target.selectionStart || 0;

    setContent(newContent);
    setCursorPosition(newCursor);

    // Check for ticker context
    const context = findTickerContext(newContent, newCursor);
    if (context) {
      setAutocompleteQuery(context.query);
      setShowAutocomplete(true);
      setAutocompleteIndex(0);
    } else {
      setShowAutocomplete(false);
      setAutocompleteQuery('');
    }
  };

  // Insert selected ticker
  const insertTicker = useCallback((ticker: string) => {
    const context = findTickerContext(content, cursorPosition);
    if (!context) return;

    const before = content.slice(0, context.dollarPos);
    const after = content.slice(cursorPosition);
    const newContent = `${before}$${ticker}${after}`;

    setContent(newContent);
    setShowAutocomplete(false);
    setAutocompleteQuery('');

    // Focus and set cursor position after the inserted ticker
    setTimeout(() => {
      if (textareaRef.current) {
        const newCursor = context.dollarPos + ticker.length + 1;
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursor, newCursor);
        setCursorPosition(newCursor);
      }
    }, 0);
  }, [content, cursorPosition, findTickerContext]);

  // Handle keyboard navigation in autocomplete
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && tickerResults.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setAutocompleteIndex((prev) =>
          prev < tickerResults.length - 1 ? prev + 1 : 0
        );
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setAutocompleteIndex((prev) =>
          prev > 0 ? prev - 1 : tickerResults.length - 1
        );
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        insertTicker(tickerResults[autocompleteIndex].ticker);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowAutocomplete(false);
        return;
      }
    }

    // Submit on Ctrl/Cmd + Enter (only if not in autocomplete mode)
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !showAutocomplete) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Close autocomplete when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        autocompleteRef.current &&
        !autocompleteRef.current.contains(e.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(e.target as Node)
      ) {
        setShowAutocomplete(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = () => {
    if (canSubmit) {
      onSubmit(content.trim());
      setContent('');
      setShowAutocomplete(false);
    }
  };

  return (
    <Card className="bg-card/60 backdrop-blur-xl">
      <CardContent className="pt-4 pb-3 space-y-3">
        <div className="relative">
          <Textarea
            ref={textareaRef}
            placeholder={placeholder}
            value={content}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onClick={(e) => setCursorPosition((e.target as HTMLTextAreaElement).selectionStart || 0)}
            className="min-h-[100px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
            disabled={isSubmitting}
          />

          {/* Autocomplete dropdown */}
          {showAutocomplete && (tickerResults.length > 0 || isSearching) && (
            <div
              ref={autocompleteRef}
              className="absolute left-0 right-0 top-full mt-1 z-50 bg-popover border border-border rounded-lg shadow-lg overflow-hidden"
            >
              {isSearching ? (
                <div className="px-3 py-2 text-sm text-muted-foreground flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Searching...
                </div>
              ) : (
                <ul className="max-h-48 overflow-y-auto">
                  {tickerResults.map((result, index) => (
                    <li key={result.ticker}>
                      <button
                        type="button"
                        onClick={() => insertTicker(result.ticker)}
                        onMouseEnter={() => setAutocompleteIndex(index)}
                        className={cn(
                          'w-full px-3 py-2 flex items-center gap-3 text-left transition-colors',
                          index === autocompleteIndex
                            ? 'bg-accent text-accent-foreground'
                            : 'hover:bg-accent/50'
                        )}
                      >
                        <TrendingUp className="h-4 w-4 text-primary flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold text-primary">
                              ${result.ticker}
                            </span>
                            {result.tradeCount > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {result.tradeCount} trades
                              </span>
                            )}
                          </div>
                          {result.name && (
                            <p className="text-xs text-muted-foreground truncate">
                              {result.name}
                            </p>
                          )}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="px-3 py-1.5 text-xs text-muted-foreground border-t border-border bg-muted/30">
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">↑↓</kbd> navigate
                <span className="mx-2">·</span>
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Enter</kbd> select
                <span className="mx-2">·</span>
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Esc</kbd> close
              </div>
            </div>
          )}
        </div>

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
              Type $ to mention tickers
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
