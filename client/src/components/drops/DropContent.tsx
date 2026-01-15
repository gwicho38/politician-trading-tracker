/**
 * DropContent Component
 * Renders drop content with $TICKER mentions as clickable links
 */

import { useState, useMemo, Fragment } from 'react';
import { TickerDetailModal } from '@/components/detail-modals/TickerDetailModal';

interface DropContentProps {
  content: string;
  className?: string;
}

// Regex to match $TICKER mentions (1-5 uppercase letters after $)
const TICKER_REGEX = /\$([A-Z]{1,5})\b/g;

export function DropContent({ content, className }: DropContentProps) {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Parse content and replace $TICKER with clickable elements
  const parsedContent = useMemo(() => {
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;

    // Reset regex lastIndex
    TICKER_REGEX.lastIndex = 0;

    let match;
    while ((match = TICKER_REGEX.exec(content)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push(content.slice(lastIndex, match.index));
      }

      // Add clickable ticker
      const ticker = match[1];
      parts.push(
        <button
          key={`${match.index}-${ticker}`}
          className="text-primary font-mono font-semibold hover:underline focus:outline-none focus:underline"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedTicker(ticker);
            setModalOpen(true);
          }}
        >
          ${ticker}
        </button>
      );

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push(content.slice(lastIndex));
    }

    return parts;
  }, [content]);

  return (
    <>
      <p className={`text-sm whitespace-pre-wrap break-words ${className || ''}`}>
        {parsedContent.map((part, index) => (
          <Fragment key={index}>{part}</Fragment>
        ))}
      </p>

      <TickerDetailModal
        ticker={selectedTicker}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </>
  );
}

export default DropContent;
