import { type Party, type DisplayTransactionType } from './typeGuards';

// Re-export Party type for backwards compatibility
export type { Party } from './typeGuards';

// Re-export formatCurrency from centralized formatters for backwards compatibility
export { formatCurrency } from './formatters';

export interface Politician {
  id: string;
  name: string;
  party: Party;
  chamber: string;
  jurisdiction: string;
  state?: string;
  avatarUrl?: string;
  totalTrades: number;
  totalVolume: number;
}

export interface Trade {
  id: string;
  politicianId: string;
  politicianName: string;
  party: Party;
  jurisdiction: string;
  ticker: string;
  company: string;
  type: Extract<DisplayTransactionType, 'buy' | 'sell'>;
  amount: string;
  estimatedValue: number;
  filingDate: string;
  transactionDate: string;
  sourceUrl?: string; // Link to the original disclosure document (PDF)
  sourceDocumentId?: string;
}

export const jurisdictions = [
  { id: 'us-house', name: 'US House', flag: '🇺🇸' },
  { id: 'us-senate', name: 'US Senate', flag: '🇺🇸' },
  { id: 'eu-parliament', name: 'EU Parliament', flag: '🇪🇺' },
  { id: 'uk-parliament', name: 'UK Parliament', flag: '🇬🇧' },
  { id: 'california', name: 'California', flag: '🌴' },
  { id: 'texas', name: 'Texas', flag: '⛳' },
];

export const mockPoliticians: Politician[] = [
  {
    id: '1',
    name: 'Nancy Pelosi',
    party: 'D',
    chamber: 'House',
    jurisdiction: 'us-house',
    state: 'CA',
    totalTrades: 156,
    totalVolume: 45000000,
  },
  {
    id: '2',
    name: 'Dan Crenshaw',
    party: 'R',
    chamber: 'House',
    jurisdiction: 'us-house',
    state: 'TX',
    totalTrades: 89,
    totalVolume: 12000000,
  },
  {
    id: '3',
    name: 'Tommy Tuberville',
    party: 'R',
    chamber: 'Senate',
    jurisdiction: 'us-senate',
    state: 'AL',
    totalTrades: 132,
    totalVolume: 8500000,
  },
  {
    id: '4',
    name: 'Mark Green',
    party: 'R',
    chamber: 'House',
    jurisdiction: 'us-house',
    state: 'TN',
    totalTrades: 67,
    totalVolume: 4200000,
  },
  {
    id: '5',
    name: 'Josh Gottheimer',
    party: 'D',
    chamber: 'House',
    jurisdiction: 'us-house',
    state: 'NJ',
    totalTrades: 98,
    totalVolume: 6700000,
  },
  {
    id: '6',
    name: 'Ursula von der Leyen',
    party: 'Other',
    chamber: 'Commission',
    jurisdiction: 'eu-parliament',
    totalTrades: 23,
    totalVolume: 1200000,
  },
];

export const mockTrades: Trade[] = [
  {
    id: 't1',
    politicianId: '1',
    politicianName: 'Nancy Pelosi',
    party: 'D',
    jurisdiction: 'us-house',
    ticker: 'NVDA',
    company: 'NVIDIA Corporation',
    type: 'buy',
    amount: '$1M - $5M',
    estimatedValue: 3000000,
    filingDate: '2024-12-15',
    transactionDate: '2024-12-10',
  },
  {
    id: 't2',
    politicianId: '3',
    politicianName: 'Tommy Tuberville',
    party: 'R',
    jurisdiction: 'us-senate',
    ticker: 'AAPL',
    company: 'Apple Inc.',
    type: 'sell',
    amount: '$100K - $250K',
    estimatedValue: 175000,
    filingDate: '2024-12-14',
    transactionDate: '2024-12-08',
  },
  {
    id: 't3',
    politicianId: '1',
    politicianName: 'Nancy Pelosi',
    party: 'D',
    jurisdiction: 'us-house',
    ticker: 'GOOGL',
    company: 'Alphabet Inc.',
    type: 'buy',
    amount: '$500K - $1M',
    estimatedValue: 750000,
    filingDate: '2024-12-13',
    transactionDate: '2024-12-06',
  },
  {
    id: 't4',
    politicianId: '2',
    politicianName: 'Dan Crenshaw',
    party: 'R',
    jurisdiction: 'us-house',
    ticker: 'MSFT',
    company: 'Microsoft Corporation',
    type: 'buy',
    amount: '$250K - $500K',
    estimatedValue: 375000,
    filingDate: '2024-12-12',
    transactionDate: '2024-12-05',
  },
  {
    id: 't5',
    politicianId: '5',
    politicianName: 'Josh Gottheimer',
    party: 'D',
    jurisdiction: 'us-house',
    ticker: 'TSLA',
    company: 'Tesla Inc.',
    type: 'sell',
    amount: '$50K - $100K',
    estimatedValue: 75000,
    filingDate: '2024-12-11',
    transactionDate: '2024-12-04',
  },
  {
    id: 't6',
    politicianId: '4',
    politicianName: 'Mark Green',
    party: 'R',
    jurisdiction: 'us-house',
    ticker: 'META',
    company: 'Meta Platforms Inc.',
    type: 'buy',
    amount: '$100K - $250K',
    estimatedValue: 180000,
    filingDate: '2024-12-10',
    transactionDate: '2024-12-03',
  },
  {
    id: 't7',
    politicianId: '3',
    politicianName: 'Tommy Tuberville',
    party: 'R',
    jurisdiction: 'us-senate',
    ticker: 'AMZN',
    company: 'Amazon.com Inc.',
    type: 'buy',
    amount: '$15K - $50K',
    estimatedValue: 32000,
    filingDate: '2024-12-09',
    transactionDate: '2024-12-02',
  },
  {
    id: 't8',
    politicianId: '6',
    politicianName: 'Ursula von der Leyen',
    party: 'Other',
    jurisdiction: 'eu-parliament',
    ticker: 'SAP',
    company: 'SAP SE',
    type: 'buy',
    amount: '€50K - €100K',
    estimatedValue: 75000,
    filingDate: '2024-12-08',
    transactionDate: '2024-12-01',
  },
];

export const chartData = [
  { month: 'Jul', buys: 45, sells: 23, volume: 12000000 },
  { month: 'Aug', buys: 52, sells: 31, volume: 18000000 },
  { month: 'Sep', buys: 38, sells: 45, volume: 15000000 },
  { month: 'Oct', buys: 67, sells: 28, volume: 22000000 },
  { month: 'Nov', buys: 58, sells: 35, volume: 19000000 },
  { month: 'Dec', buys: 72, sells: 41, volume: 25000000 },
];

export const stats = {
  totalTrades: 1247,
  totalVolume: 156000000,
  activePoliticians: 284,
  jurisdictionsTracked: 6,
  averageTradeSize: 125000,
  recentFilings: 89,
};

// formatCurrency is now re-exported from './formatters' at the top of the file
// The original implementation has been consolidated into lib/formatters.ts

/**
 * @deprecated Use partyUtils.getPartyColor with useParties() instead.
 * Kept during migration — returns a Tailwind class for legacy callers.
 */
export const getPartyColor = (party: string): string => {
  const map: Record<string, string> = {
    D: 'text-blue-400', 'S&D': 'text-blue-400',
    R: 'text-red-400', ECR: 'text-red-400',
    I: 'text-yellow-400', Renew: 'text-yellow-400',
    EPP: 'text-sky-400', 'Greens/EFA': 'text-green-400',
    ID: 'text-indigo-400', 'GUE/NGL': 'text-rose-400',
    NI: 'text-slate-400',
  };
  return map[party] || 'text-muted-foreground';
};

/**
 * @deprecated Use partyUtils.partyBadgeStyle with useParties() instead.
 */
export const getPartyBg = (party: string): string => {
  const map: Record<string, string> = {
    D: 'bg-blue-500/20 border-blue-500/30', 'S&D': 'bg-blue-500/20 border-blue-500/30',
    R: 'bg-red-500/20 border-red-500/30', ECR: 'bg-red-500/20 border-red-500/30',
    I: 'bg-yellow-500/20 border-yellow-500/30', Renew: 'bg-yellow-500/20 border-yellow-500/30',
    EPP: 'bg-sky-500/20 border-sky-500/30', 'Greens/EFA': 'bg-green-500/20 border-green-500/30',
    ID: 'bg-indigo-500/20 border-indigo-500/30', 'GUE/NGL': 'bg-rose-500/20 border-rose-500/30',
    NI: 'bg-slate-500/20 border-slate-500/30',
  };
  return map[party] || 'bg-muted border-border';
};
