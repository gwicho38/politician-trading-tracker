import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  delay?: number;
}

const StatsCard = ({ title, value, change, changeType = 'neutral', icon: Icon, delay = 0 }: StatsCardProps) => {
  return (
    <div
      className="group relative overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 sm:p-6 transition-all duration-300 hover:border-primary/30 hover:shadow-lg"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Glow effect on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
      </div>

      <div className="relative flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-xs sm:text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-1 sm:mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-foreground truncate">
            {value}
          </p>
          {change && (
            <p className={cn(
              "mt-1 text-sm font-medium",
              changeType === 'positive' && "text-success",
              changeType === 'negative' && "text-destructive",
              changeType === 'neutral' && "text-muted-foreground"
            )}>
              {change}
            </p>
          )}
        </div>
        <div className="rounded-lg bg-primary/10 p-2 sm:p-3 border border-primary/20 flex-shrink-0">
          <Icon className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
        </div>
      </div>
    </div>
  );
};

export default StatsCard;
