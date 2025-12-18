import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import type { Tables } from '@/integrations/supabase/types';

type Trade = Tables<'trades'>;
type Politician = Tables<'politicians'>;

interface TradeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trade?: Trade | null;
  onSuccess: () => void;
}

const AMOUNT_RANGES = [
  '$1 - $1,000',
  '$1,001 - $15,000',
  '$15,001 - $50,000',
  '$50,001 - $100,000',
  '$100,001 - $250,000',
  '$250,001 - $500,000',
  '$500,001 - $1,000,000',
  '$1,000,001 - $5,000,000',
  '$5,000,001 - $25,000,000',
  '$25,000,001 - $50,000,000',
  'Over $50,000,000',
];

const TradeForm = ({ open, onOpenChange, trade, onSuccess }: TradeFormProps) => {
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    politician_id: '',
    ticker: '',
    company: '',
    trade_type: 'buy',
    amount_range: '$15,001 - $50,000',
    estimated_value: '',
    transaction_date: '',
    filing_date: '',
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchPoliticians();
  }, []);

  useEffect(() => {
    if (trade) {
      setFormData({
        politician_id: trade.politician_id || '',
        ticker: trade.ticker,
        company: trade.company,
        trade_type: trade.trade_type,
        amount_range: trade.amount_range,
        estimated_value: trade.estimated_value.toString(),
        transaction_date: trade.transaction_date,
        filing_date: trade.filing_date,
      });
    } else {
      setFormData({
        politician_id: '',
        ticker: '',
        company: '',
        trade_type: 'buy',
        amount_range: '$15,001 - $50,000',
        estimated_value: '',
        transaction_date: new Date().toISOString().split('T')[0],
        filing_date: new Date().toISOString().split('T')[0],
      });
    }
  }, [trade, open]);

  const fetchPoliticians = async () => {
    const { data } = await supabase.from('politicians').select('*').order('name');
    if (data) setPoliticians(data);
  };

  const handleSubmit = async () => {
    if (!formData.ticker || !formData.company || !formData.estimated_value) {
      toast({ title: 'Error', description: 'Please fill in required fields', variant: 'destructive' });
      return;
    }

    setIsLoading(true);

    const payload = {
      politician_id: formData.politician_id || null,
      ticker: formData.ticker.toUpperCase(),
      company: formData.company,
      trade_type: formData.trade_type,
      amount_range: formData.amount_range,
      estimated_value: parseInt(formData.estimated_value),
      transaction_date: formData.transaction_date,
      filing_date: formData.filing_date,
    };

    let error;
    if (trade) {
      const result = await supabase.from('trades').update(payload).eq('id', trade.id);
      error = result.error;
    } else {
      const result = await supabase.from('trades').insert(payload);
      error = result.error;
    }

    setIsLoading(false);

    if (error) {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    } else {
      toast({ title: 'Success', description: trade ? 'Trade updated' : 'Trade created' });
      onOpenChange(false);
      onSuccess();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{trade ? 'Edit Trade' : 'Add Trade'}</DialogTitle>
          <DialogDescription>
            {trade ? 'Update trade details' : 'Record a new trade'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
          <div className="space-y-2">
            <Label>Politician</Label>
            <Select
              value={formData.politician_id}
              onValueChange={(value) => setFormData(prev => ({ ...prev, politician_id: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select politician" />
              </SelectTrigger>
              <SelectContent>
                {politicians.map(p => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name} ({p.party})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ticker">Ticker *</Label>
              <Input
                id="ticker"
                value={formData.ticker}
                onChange={(e) => setFormData(prev => ({ ...prev, ticker: e.target.value.toUpperCase() }))}
                placeholder="e.g., AAPL"
                maxLength={10}
              />
            </div>
            <div className="space-y-2">
              <Label>Trade Type *</Label>
              <Select
                value={formData.trade_type}
                onValueChange={(value) => setFormData(prev => ({ ...prev, trade_type: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy">Buy</SelectItem>
                  <SelectItem value="sell">Sell</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="company">Company *</Label>
            <Input
              id="company"
              value={formData.company}
              onChange={(e) => setFormData(prev => ({ ...prev, company: e.target.value }))}
              placeholder="Company name"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Amount Range</Label>
              <Select
                value={formData.amount_range}
                onValueChange={(value) => setFormData(prev => ({ ...prev, amount_range: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AMOUNT_RANGES.map(range => (
                    <SelectItem key={range} value={range}>{range}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="estimated_value">Estimated Value ($) *</Label>
              <Input
                id="estimated_value"
                type="number"
                value={formData.estimated_value}
                onChange={(e) => setFormData(prev => ({ ...prev, estimated_value: e.target.value }))}
                placeholder="e.g., 50000"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="transaction_date">Transaction Date *</Label>
              <Input
                id="transaction_date"
                type="date"
                value={formData.transaction_date}
                onChange={(e) => setFormData(prev => ({ ...prev, transaction_date: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filing_date">Filing Date *</Label>
              <Input
                id="filing_date"
                type="date"
                value={formData.filing_date}
                onChange={(e) => setFormData(prev => ({ ...prev, filing_date: e.target.value }))}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Saving...' : trade ? 'Update' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TradeForm;
