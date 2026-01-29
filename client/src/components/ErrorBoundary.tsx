import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { logError, logInfo } from '@/lib/logger';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback component */
  fallback?: ReactNode;
  /** Callback when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Keys that trigger reset when changed */
  resetKeys?: Array<string | number>;
  /** Name for logging/debugging */
  name?: string;
  /** Show minimal error UI (for smaller components) */
  minimal?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component that catches JavaScript errors in child components
 * and displays a fallback UI instead of crashing the whole app.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary name="Dashboard" onError={logError}>
 *   <Dashboard />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to structured logger
    const boundaryName = this.props.name ? `ErrorBoundary:${this.props.name}` : 'ErrorBoundary';
    logError(`[${boundaryName}] Caught error`, 'error-boundary', error, {
      componentStack: errorInfo.componentStack,
    });

    this.setState({ errorInfo });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    // Reset error state if resetKeys change
    if (this.state.hasError && this.props.resetKeys) {
      const prevKeys = prevProps.resetKeys || [];
      const hasKeyChanged = this.props.resetKeys.some(
        (key, index) => key !== prevKeys[index]
      );
      if (hasKeyChanged) {
        this.reset();
      }
    }
  }

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback takes precedence
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Minimal error UI for smaller components
      if (this.props.minimal) {
        return (
          <MinimalErrorFallback
            error={this.state.error}
            onRetry={this.reset}
          />
        );
      }

      // Full error UI for larger sections
      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.reset}
          name={this.props.name}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * Full error fallback UI for major sections
 */
interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onRetry: () => void;
  name?: string;
}

function ErrorFallback({ error, errorInfo, onRetry, name }: ErrorFallbackProps) {
  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleReportError = () => {
    // Could integrate with error reporting service
    const errorDetails = {
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      location: window.location.href,
      timestamp: new Date().toISOString(),
    };
    logInfo('Error report', 'error-boundary', errorDetails);
    // TODO: Send to error reporting service (e.g., Sentry)
  };

  return (
    <div className="flex min-h-[400px] items-center justify-center p-6">
      <Card className="w-full max-w-lg border-destructive/50">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            {name ? `The ${name} section` : 'This section'} encountered an error
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <Bug className="h-4 w-4" />
              <AlertTitle>Error Details</AlertTitle>
              <AlertDescription className="mt-2 font-mono text-xs break-all">
                {error.message}
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Button onClick={onRetry} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
            <Button variant="outline" onClick={handleGoHome} className="gap-2">
              <Home className="h-4 w-4" />
              Go Home
            </Button>
          </div>

          <p className="text-center text-xs text-muted-foreground">
            If this problem persists, please{' '}
            <button
              onClick={handleReportError}
              className="text-primary underline hover:no-underline"
            >
              report the issue
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Minimal error fallback for smaller components
 */
interface MinimalErrorFallbackProps {
  error: Error | null;
  onRetry: () => void;
}

function MinimalErrorFallback({ error, onRetry }: MinimalErrorFallbackProps) {
  return (
    <Alert variant="destructive" className="my-4">
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Error loading content</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span className="text-sm truncate max-w-[200px]">
          {error?.message || 'An unexpected error occurred'}
        </span>
        <Button size="sm" variant="outline" onClick={onRetry} className="ml-4 shrink-0">
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}

/**
 * Hook-friendly wrapper for using error boundaries with function components
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<ErrorBoundaryProps, 'children'> = {}
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...options}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name || 'Component'})`;

  return WrappedComponent;
}

export default ErrorBoundary;
