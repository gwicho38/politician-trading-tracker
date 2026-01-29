import { cn } from '@/lib/utils';

interface SkipLinkProps {
  href?: string;
  children?: React.ReactNode;
  className?: string;
}

/**
 * Accessible skip-to-content link for keyboard navigation.
 * Hidden visually but appears on focus, allowing keyboard users
 * to skip navigation and jump directly to main content.
 *
 * WCAG 2.4.1 - Bypass Blocks compliance
 */
export function SkipLink({
  href = '#main-content',
  children = 'Skip to main content',
  className,
}: SkipLinkProps) {
  return (
    <a
      href={href}
      className={cn(
        // Visually hidden by default
        'sr-only',
        // Visible when focused
        'focus:not-sr-only',
        'focus:fixed focus:top-4 focus:left-4 focus:z-[100]',
        'focus:px-4 focus:py-2',
        'focus:bg-primary focus:text-primary-foreground',
        'focus:rounded-md focus:shadow-lg',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        'font-medium text-sm',
        'transition-colors',
        className
      )}
    >
      {children}
    </a>
  );
}

export default SkipLink;
