import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-border",
        // Improved contrast: darker text colors for better accessibility (WCAG AA)
        success: "border-success/40 bg-success/15 text-green-700 dark:text-green-400",
        warning: "border-warning/40 bg-warning/15 text-amber-700 dark:text-amber-400",
        buy: "border-success/40 bg-success/15 text-green-700 dark:text-green-400 font-mono",
        sell: "border-destructive/40 bg-destructive/15 text-red-700 dark:text-red-400 font-mono",
        jurisdiction: "border-border/50 bg-secondary/50 text-foreground/80 hover:bg-secondary hover:text-foreground transition-colors cursor-pointer",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
