import { useState } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/integrations/supabase/client';
import type { TradingDisclosure } from '@/hooks/useSupabaseData';
import { formatDate, formatAmountRange } from '@/lib/formatters';
import { logError } from '@/lib/logger';

const ERROR_TYPES = [
  { value: 'wrong_amount', label: 'Wrong Amount' },
  { value: 'wrong_date', label: 'Wrong Date' },
  { value: 'wrong_ticker', label: 'Wrong Ticker' },
  { value: 'wrong_politician', label: 'Wrong Politician' },
  { value: 'other', label: 'Other' },
] as const;

type ErrorType = typeof ERROR_TYPES[number]['value'];

interface ReportErrorModalProps {
  disclosure: TradingDisclosure | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ReportErrorModal({ disclosure, open, onOpenChange }: ReportErrorModalProps) {
  const { user } = useAuth();
  const { toast } = useToast();

  const [errorType, setErrorType] = useState<ErrorType | ''>('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const resetForm = () => {
    setErrorType('');
    setDescription('');
  };

  const handleClose = () => {
    resetForm();
    onOpenChange(false);
  };

  const handleSubmit = async () => {
    if (!user) {
      toast({
        title: 'Authentication required',
        description: 'Please sign in to report errors.',
        variant: 'destructive',
      });
      return;
    }

    if (!disclosure) return;

    if (!errorType) {
      toast({
        title: 'Error type required',
        description: 'Please select an error type.',
        variant: 'destructive',
      });
      return;
    }

    if (description.trim().length < 10) {
      toast({
        title: 'Description too short',
        description: 'Please provide at least 10 characters describing the error.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Create snapshot of disclosure data for reference
      const disclosureSnapshot = {
        id: disclosure.id,
        politician_name: disclosure.politician?.name,
        politician_party: disclosure.politician?.party,
        asset_name: disclosure.asset_name,
        asset_ticker: disclosure.asset_ticker,
        transaction_type: disclosure.transaction_type,
        amount_range_min: disclosure.amount_range_min,
        amount_range_max: disclosure.amount_range_max,
        transaction_date: disclosure.transaction_date,
        disclosure_date: disclosure.disclosure_date,
        source_url: disclosure.source_url,
      };

      // Add timeout to prevent endless spinner
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timed out. Please try again.')), 15000)
      );

      const insertPromise = supabase
        .from('user_error_reports')
        .insert({
          user_id: user.id,
          disclosure_id: disclosure.id,
          error_type: errorType,
          description: description.trim(),
          disclosure_snapshot: disclosureSnapshot,
        });

      const { error } = await Promise.race([insertPromise, timeoutPromise]) as { error: Error | null };

      if (error) throw error;

      toast({
        title: 'Report submitted',
        description: 'Thank you for helping improve data quality. We will review your report.',
      });

      handleClose();
    } catch (error) {
      logError('Error submitting report', 'report', error instanceof Error ? error : undefined);
      toast({
        title: 'Failed to submit report',
        description: error instanceof Error ? error.message : 'Please try again later.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // formatDate and formatAmountRange are imported from '@/lib/formatters'
  const formatAmount = (min: number | null, max: number | null) => {
    if (min === null && max === null) return 'Not disclosed';
    return formatAmountRange(min, max);
  };

  if (!disclosure) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Report Data Error
          </DialogTitle>
          <DialogDescription>
            Help us improve data quality by reporting errors you find between the parsed data and the original PDF.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Disclosure Summary */}
          <div className="rounded-lg border border-border/50 bg-muted/30 p-4 space-y-2">
            <div className="text-sm font-medium text-muted-foreground">Disclosure being reported:</div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Politician:</span>
                <span className="font-medium">
                  {disclosure.politician?.name || 'Unknown'}
                  {disclosure.politician?.party && (
                    <Badge variant="outline" className="ml-2 text-xs">
                      {disclosure.politician.party}
                    </Badge>
                  )}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Asset:</span>
                <span className="font-medium">
                  {disclosure.asset_ticker && (
                    <span className="font-mono text-primary mr-1">{disclosure.asset_ticker}</span>
                  )}
                  <span className="text-muted-foreground truncate max-w-[200px] inline-block align-bottom">
                    {disclosure.asset_name}
                  </span>
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type:</span>
                <span className="font-medium capitalize">{disclosure.transaction_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Amount:</span>
                <span className="font-medium">
                  {formatAmount(disclosure.amount_range_min, disclosure.amount_range_max)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Transaction Date:</span>
                <span className="font-medium">{formatDate(disclosure.transaction_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Disclosure Date:</span>
                <span className="font-medium">{formatDate(disclosure.disclosure_date)}</span>
              </div>
              {disclosure.source_url && (
                <div className="pt-2">
                  <a
                    href={disclosure.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    View original PDF disclosure →
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Error Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="error-type">What type of error did you find? *</Label>
            <Select value={errorType} onValueChange={(v) => setErrorType(v as ErrorType)}>
              <SelectTrigger id="error-type">
                <SelectValue placeholder="Select error type" />
              </SelectTrigger>
              <SelectContent>
                {ERROR_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Describe the error *</Label>
            <Textarea
              id="description"
              placeholder="Please describe what's incorrect and what the correct value should be (from the PDF)..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[100px]"
            />
            <p className="text-xs text-muted-foreground">
              Minimum 10 characters. Be specific about what's wrong and what it should be.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || !errorType || description.trim().length < 10}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Submitting...
              </>
            ) : (
              'Submit Report'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
