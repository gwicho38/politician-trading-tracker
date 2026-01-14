/**
 * LambdaEditor Component
 * Monaco editor for writing custom Python lambda code to transform signals
 */

import { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import {
  Code,
  Play,
  RotateCcw,
  HelpCircle,
  CheckCircle,
  AlertCircle,
  Maximize2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { LambdaTemplates } from './LambdaTemplates';

const DEFAULT_LAMBDA = `# Modify signal fields and assign to 'result'
# Available: signal (dict), math module, Decimal

# Example: Boost confidence for high buy/sell ratio
if signal.get('buy_sell_ratio', 0) > 3.0:
    signal['confidence_score'] = min(signal['confidence_score'] + 0.05, 0.99)

# Example: Penalize low politician count
if signal.get('politician_activity_count', 0) < 3:
    signal['confidence_score'] = signal['confidence_score'] * 0.9

result = signal
`;

const HELP_EXAMPLES = [
  {
    name: 'Boost high activity',
    code: `if signal.get('politician_activity_count', 0) >= 5:
    signal['confidence_score'] = min(signal['confidence_score'] + 0.1, 0.99)
result = signal`,
  },
  {
    name: 'Convert weak sells to holds',
    code: `if signal['signal_type'] == 'sell' and signal['confidence_score'] < 0.7:
    signal['signal_type'] = 'hold'
    signal['signal_strength'] = 'weak'
result = signal`,
  },
  {
    name: 'Require bipartisan support',
    code: `features = signal.get('features', {})
if not features.get('bipartisan', False):
    signal['confidence_score'] = signal['confidence_score'] * 0.8
result = signal`,
  },
];

interface LambdaEditorProps {
  value: string;
  onChange: (code: string) => void;
  onApply: () => void;
  error?: string | null;
  isLoading?: boolean;
  lambdaApplied?: boolean;
}

export function LambdaEditor({
  value,
  onChange,
  onApply,
  error,
  isLoading,
  lambdaApplied,
}: LambdaEditorProps) {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const currentValue = value || DEFAULT_LAMBDA;

  const handleReset = useCallback(() => {
    onChange(DEFAULT_LAMBDA);
  }, [onChange]);

  const handleExampleClick = useCallback((code: string) => {
    onChange(code);
    setIsHelpOpen(false);
  }, [onChange]);

  // Editor content (shared between normal and full-screen mode)
  const editorContent = (height: string = '100%') => (
    <div className={`rounded-md border overflow-hidden ${isFullScreen ? '' : 'flex-1 min-h-[300px]'}`} style={{ height }}>
      <Editor
        height="100%"
        language="python"
        theme="vs-dark"
        value={currentValue}
        onChange={(v) => onChange(v || '')}
        options={{
          minimap: { enabled: isFullScreen },
          fontSize: isFullScreen ? 14 : 12,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: 'on',
          scrollbar: {
            vertical: 'auto',
            horizontal: 'auto',
          },
        }}
      />
    </div>
  );

  return (
    <>
      <Card className="flex flex-col h-full">
        <CardHeader className="pb-3 shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Code className="h-4 w-4" />
              Custom Signal Transform
              {lambdaApplied && (
                <Badge variant="outline" className="text-xs ml-2">
                  <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                  Applied
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setIsFullScreen(true)}
                  >
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Full-screen editor</TooltipContent>
              </Tooltip>
              <LambdaTemplates onSelect={(code) => onChange(code)} />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setIsHelpOpen(!isHelpOpen)}
                  >
                    <HelpCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>View examples and help</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 flex-1 flex flex-col min-h-0">
          {/* Help/Examples Section */}
          <Collapsible open={isHelpOpen} onOpenChange={setIsHelpOpen}>
            <CollapsibleContent className="space-y-3 pb-3">
              <div className="text-sm text-muted-foreground">
                <p className="mb-2">
                  Write Python code to transform each signal. The code has access to:
                </p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li><code className="bg-muted px-1 rounded">signal</code> - Dictionary with signal fields</li>
                  <li><code className="bg-muted px-1 rounded">math</code> - Math functions (sqrt, log, sin, etc.)</li>
                  <li><code className="bg-muted px-1 rounded">Decimal</code> - Precise decimal arithmetic</li>
                  <li>Basic builtins: len, abs, min, max, round, str, int, float</li>
                </ul>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium">Quick Examples:</p>
                <div className="flex flex-wrap gap-2">
                  {HELP_EXAMPLES.map((example) => (
                    <Button
                      key={example.name}
                      variant="outline"
                      size="sm"
                      className="text-xs h-7"
                      onClick={() => handleExampleClick(example.code)}
                    >
                      {example.name}
                    </Button>
                  ))}
                </div>
              </div>
              <div className="text-xs text-muted-foreground border-t pt-2">
                <strong>Signal fields:</strong> ticker, signal_type, signal_strength,
                confidence_score, politician_activity_count, buy_sell_ratio,
                total_transaction_volume, features
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Monaco Editor */}
          {editorContent()}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="shrink-0">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 shrink-0">
            <Button
              size="sm"
              onClick={onApply}
              disabled={isLoading || !currentValue.trim()}
              className="flex-1"
            >
              {isLoading ? (
                <>
                  <span className="animate-spin mr-2">...</span>
                  Applying...
                </>
              ) : (
                <>
                  <Play className="h-3 w-3 mr-1" />
                  Apply Lambda
                </>
              )}
            </Button>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleReset}
                  disabled={currentValue === DEFAULT_LAMBDA}
                >
                  <RotateCcw className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reset to default</TooltipContent>
            </Tooltip>
          </div>
        </CardContent>
      </Card>

      {/* Full-screen Dialog */}
      <Dialog open={isFullScreen} onOpenChange={setIsFullScreen}>
        <DialogContent className="max-w-[90vw] w-[90vw] h-[90vh] flex flex-col p-0">
          <DialogHeader className="p-4 pb-2 border-b shrink-0">
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Lambda Editor
                {lambdaApplied && (
                  <Badge variant="outline" className="text-xs ml-2">
                    <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                    Applied
                  </Badge>
                )}
              </DialogTitle>
              <div className="flex items-center gap-2">
                <LambdaTemplates onSelect={(code) => onChange(code)} />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  disabled={currentValue === DEFAULT_LAMBDA}
                >
                  <RotateCcw className="h-4 w-4 mr-1" />
                  Reset
                </Button>
                <Button
                  size="sm"
                  onClick={onApply}
                  disabled={isLoading || !currentValue.trim()}
                >
                  {isLoading ? 'Applying...' : (
                    <>
                      <Play className="h-4 w-4 mr-1" />
                      Apply
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogHeader>
          <div className="flex-1 p-4 overflow-hidden flex flex-col gap-4">
            {/* Error in full-screen mode */}
            {error && (
              <Alert variant="destructive" className="shrink-0">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error}
                </AlertDescription>
              </Alert>
            )}
            {/* Full-height editor */}
            {editorContent('100%')}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default LambdaEditor;
