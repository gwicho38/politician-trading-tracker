import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import type { Tables } from '@/integrations/supabase/types';

type Politician = Tables<'politicians'>;
type Jurisdiction = Tables<'jurisdictions'>;

interface PoliticianFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  politician?: Politician | null;
  onSuccess: () => void;
}

const PoliticianForm = ({ open, onOpenChange, politician, onSuccess }: PoliticianFormProps) => {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    party: 'D',
    chamber: 'House',
    state: '',
    jurisdiction_id: '',
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchJurisdictions();
  }, []);

  useEffect(() => {
    if (politician) {
      setFormData({
        name: politician.name,
        party: politician.party,
        chamber: politician.chamber,
        state: politician.state || '',
        jurisdiction_id: politician.jurisdiction_id || '',
      });
    } else {
      setFormData({
        name: '',
        party: 'D',
        chamber: 'House',
        state: '',
        jurisdiction_id: '',
      });
    }
  }, [politician, open]);

  const fetchJurisdictions = async () => {
    const { data } = await supabase.from('jurisdictions').select('*').order('name');
    if (data) setJurisdictions(data);
  };

  const handleSubmit = async () => {
    if (!formData.name) {
      toast({ title: 'Error', description: 'Name is required', variant: 'destructive' });
      return;
    }

    setIsLoading(true);
    
    const payload = {
      name: formData.name,
      party: formData.party,
      chamber: formData.chamber,
      state: formData.state || null,
      jurisdiction_id: formData.jurisdiction_id || null,
    };

    let error;
    if (politician) {
      const result = await supabase.from('politicians').update(payload).eq('id', politician.id);
      error = result.error;
    } else {
      const result = await supabase.from('politicians').insert(payload);
      error = result.error;
    }

    setIsLoading(false);

    if (error) {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    } else {
      toast({ title: 'Success', description: politician ? 'Politician updated' : 'Politician created' });
      onOpenChange(false);
      onSuccess();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{politician ? 'Edit Politician' : 'Add Politician'}</DialogTitle>
          <DialogDescription>
            {politician ? 'Update politician details' : 'Add a new politician to track'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Full name"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Party *</Label>
              <Select
                value={formData.party}
                onValueChange={(value) => setFormData(prev => ({ ...prev, party: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="D">Democrat</SelectItem>
                  <SelectItem value="R">Republican</SelectItem>
                  <SelectItem value="I">Independent</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Chamber *</Label>
              <Select
                value={formData.chamber}
                onValueChange={(value) => setFormData(prev => ({ ...prev, chamber: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="House">House</SelectItem>
                  <SelectItem value="Senate">Senate</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="state">State</Label>
              <Input
                id="state"
                value={formData.state}
                onChange={(e) => setFormData(prev => ({ ...prev, state: e.target.value }))}
                placeholder="e.g., CA, TX"
                maxLength={2}
              />
            </div>
            <div className="space-y-2">
              <Label>Jurisdiction</Label>
              <Select
                value={formData.jurisdiction_id}
                onValueChange={(value) => setFormData(prev => ({ ...prev, jurisdiction_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select jurisdiction" />
                </SelectTrigger>
                <SelectContent>
                  {jurisdictions.map(j => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.flag} {j.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Saving...' : politician ? 'Update' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PoliticianForm;
