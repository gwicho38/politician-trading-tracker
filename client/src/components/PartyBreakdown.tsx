import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Loader2 } from 'lucide-react';
import { usePoliticians } from '@/hooks/useSupabaseData';

const PARTY_COLORS: Record<string, string> = {
  D: 'hsl(221, 83%, 53%)', // Blue for Democrats
  R: 'hsl(0, 72%, 51%)',   // Red for Republicans
  I: 'hsl(142, 71%, 45%)', // Green for Independents
  Other: 'hsl(var(--muted-foreground))',
};

const PARTY_LABELS: Record<string, string> = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
  Other: 'Other',
};

const PartyBreakdown = () => {
  const { data: politicians, isLoading } = usePoliticians();

  // Calculate party breakdown from politicians data
  const partyData = politicians?.reduce((acc, p) => {
    const party = p.party || 'Other';
    const key = ['D', 'R', 'I'].includes(party) ? party : 'Other';
    const existing = acc.find(item => item.party === key);
    if (existing) {
      existing.trades += p.total_trades || 0;
      existing.volume += p.total_volume || 0;
      existing.count += 1;
    } else {
      acc.push({
        party: key,
        name: PARTY_LABELS[key],
        trades: p.total_trades || 0,
        volume: p.total_volume || 0,
        count: 1,
      });
    }
    return acc;
  }, [] as Array<{ party: string; name: string; trades: number; volume: number; count: number }>);

  // Sort by trades
  partyData?.sort((a, b) => b.trades - a.trades);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!partyData || partyData.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-foreground">Party Breakdown</h3>
        <p className="text-sm text-muted-foreground">Trading activity by political party</p>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={partyData}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={70}
              paddingAngle={2}
              dataKey="trades"
              nameKey="name"
            >
              {partyData.map((entry) => (
                <Cell
                  key={entry.party}
                  fill={PARTY_COLORS[entry.party] || PARTY_COLORS.Other}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
              formatter={(value: number, name: string) => [
                `${value.toLocaleString()} trades`,
                name,
              ]}
            />
            <Legend
              verticalAlign="middle"
              align="right"
              layout="vertical"
              iconType="circle"
              iconSize={8}
              formatter={(value, entry) => {
                const data = partyData.find(p => p.name === value);
                return (
                  <span className="text-xs text-muted-foreground">
                    {value} ({data?.count || 0})
                  </span>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PartyBreakdown;
