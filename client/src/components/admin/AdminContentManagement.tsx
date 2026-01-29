import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { Users2, TrendingUp, Trash2, RefreshCw, Plus, Pencil } from 'lucide-react';
import type { Tables } from '@/integrations/supabase/types';
import PoliticianForm from './PoliticianForm';
import TradeForm from './TradeForm';
import { formatCurrencyCompact, formatDate as formatDateUtil } from '@/lib/formatters';
import { logError } from '@/lib/logger';

type Politician = Tables<'politicians'>;
type Trade = Tables<'trades'>;

const AdminContentManagement = () => {
  const [politicians, setPoliticians] = useState<Politician[]>([]);
  const [trades, setTrades] = useState<(Trade & { politician_name?: string })[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [politicianFormOpen, setPoliticianFormOpen] = useState(false);
  const [tradeFormOpen, setTradeFormOpen] = useState(false);
  const [editingPolitician, setEditingPolitician] = useState<Politician | null>(null);
  const [editingTrade, setEditingTrade] = useState<Trade | null>(null);
  const { toast } = useToast();

  // Separate pagination for each tab
  const politiciansPagination = usePagination();
  const tradesPagination = usePagination();

  // Update pagination when data changes
  useEffect(() => {
    politiciansPagination.setTotalItems(politicians.length);
  }, [politicians.length]);

  useEffect(() => {
    tradesPagination.setTotalItems(trades.length);
  }, [trades.length]);

  // Paginate data
  const paginatedPoliticians = politicians.slice(politiciansPagination.startIndex, politiciansPagination.endIndex);
  const paginatedTrades = trades.slice(tradesPagination.startIndex, tradesPagination.endIndex);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [politiciansRes, tradesRes] = await Promise.all([
        supabase.from('politicians').select('*').order('name'),
        supabase.from('trades').select(`
          *,
          politicians(name)
        `).order('filing_date', { ascending: false }).limit(500),
      ]);

      if (politiciansRes.error) throw politiciansRes.error;
      if (tradesRes.error) throw tradesRes.error;

      setPoliticians(politiciansRes.data || []);
      setTrades((tradesRes.data || []).map(t => ({
        ...t,
        politician_name: (t.politicians as any)?.name,
      })));
    } catch (error) {
      logError('Error fetching data', 'admin', error instanceof Error ? error : undefined);
      toast({
        title: 'Error',
        description: 'Failed to fetch content data',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const deletePolitician = async (id: string) => {
    try {
      const { error } = await supabase.from('politicians').delete().eq('id', id);
      if (error) throw error;
      
      toast({ title: 'Success', description: 'Politician deleted' });
      fetchData();
    } catch (error) {
      logError('Error deleting politician', 'admin', error instanceof Error ? error : undefined);
      toast({
        title: 'Error',
        description: 'Failed to delete politician',
        variant: 'destructive',
      });
    }
  };

  const deleteTrade = async (id: string) => {
    try {
      const { error } = await supabase.from('trades').delete().eq('id', id);
      if (error) throw error;
      
      toast({ title: 'Success', description: 'Trade deleted' });
      fetchData();
    } catch (error) {
      logError('Error deleting trade', 'admin', error instanceof Error ? error : undefined);
      toast({
        title: 'Error',
        description: 'Failed to delete trade',
        variant: 'destructive',
      });
    }
  };

  // formatCurrencyCompact and formatDateUtil are imported from '@/lib/formatters'
  const formatCurrency = formatCurrencyCompact;
  const formatDate = (dateString: string) => formatDateUtil(dateString);

  const getPartyBadgeVariant = (party: string) => {
    if (party.toLowerCase().includes('democrat')) return 'default';
    if (party.toLowerCase().includes('republican')) return 'destructive';
    return 'secondary';
  };

  const openEditPolitician = (politician: Politician) => {
    setEditingPolitician(politician);
    setPoliticianFormOpen(true);
  };

  const openEditTrade = (trade: Trade) => {
    setEditingTrade(trade);
    setTradeFormOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Content Management</h2>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <PoliticianForm
        open={politicianFormOpen}
        onOpenChange={(open) => {
          setPoliticianFormOpen(open);
          if (!open) setEditingPolitician(null);
        }}
        politician={editingPolitician}
        onSuccess={fetchData}
      />

      <TradeForm
        open={tradeFormOpen}
        onOpenChange={(open) => {
          setTradeFormOpen(open);
          if (!open) setEditingTrade(null);
        }}
        trade={editingTrade}
        onSuccess={fetchData}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Politicians</CardTitle>
            <Users2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{politicians.length}</div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Trades Tracked</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{trades.length}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="politicians" className="space-y-4">
        <TabsList className="glass">
          <TabsTrigger value="politicians">Politicians</TabsTrigger>
          <TabsTrigger value="trades">Trades</TabsTrigger>
        </TabsList>

        <TabsContent value="politicians">
          <Card className="glass">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Politicians</CardTitle>
                <CardDescription>Manage tracked politicians</CardDescription>
              </div>
              <Button size="sm" onClick={() => setPoliticianFormOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Politician
              </Button>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : (
                <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Party</TableHead>
                      <TableHead>Chamber</TableHead>
                      <TableHead>State</TableHead>
                      <TableHead>Trades</TableHead>
                      <TableHead>Volume</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedPoliticians.map(politician => (
                      <TableRow key={politician.id}>
                        <TableCell className="font-medium">{politician.name}</TableCell>
                        <TableCell>
                          <Badge variant={getPartyBadgeVariant(politician.party)}>
                            {politician.party}
                          </Badge>
                        </TableCell>
                        <TableCell>{politician.chamber}</TableCell>
                        <TableCell>{politician.state || '-'}</TableCell>
                        <TableCell>{politician.total_trades}</TableCell>
                        <TableCell>{formatCurrency(politician.total_volume)}</TableCell>
                        <TableCell className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditPolitician(politician)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={() => deletePolitician(politician.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    {paginatedPoliticians.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                          No politicians found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>

                {/* Pagination Controls */}
                {politicians.length > 0 && (
                  <PaginationControls pagination={politiciansPagination} itemLabel="politicians" />
                )}
              </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trades">
          <Card className="glass">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Trades</CardTitle>
                <CardDescription>Manage trade records</CardDescription>
              </div>
              <Button size="sm" onClick={() => setTradeFormOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Trade
              </Button>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : (
                <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Politician</TableHead>
                      <TableHead>Ticker</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Filed</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedTrades.map(trade => (
                      <TableRow key={trade.id}>
                        <TableCell className="font-medium">
                          {trade.politician_name || 'Unknown'}
                        </TableCell>
                        <TableCell className="font-mono">{trade.ticker}</TableCell>
                        <TableCell>{trade.company}</TableCell>
                        <TableCell>
                          <Badge variant={trade.trade_type === 'buy' ? 'default' : 'destructive'}>
                            {trade.trade_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatCurrency(trade.estimated_value)}</TableCell>
                        <TableCell>{formatDate(trade.filing_date)}</TableCell>
                        <TableCell className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditTrade(trade)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={() => deleteTrade(trade.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    {paginatedTrades.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                          No trades found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>

                {/* Pagination Controls */}
                {trades.length > 0 && (
                  <PaginationControls pagination={tradesPagination} itemLabel="trades" />
                )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdminContentManagement;
