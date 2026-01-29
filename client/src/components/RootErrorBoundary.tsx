import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Mail } from 'lucide-react';
import { logError } from '@/lib/logger';

// Support email from environment variable with fallback
const SUPPORT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL || 'support@govmarket.trade';

interface RootErrorBoundaryProps {
  children: ReactNode;
}

interface RootErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Root-level error boundary for the entire application.
 * Shows a full-page error screen when the app crashes.
 * Uses minimal dependencies to avoid cascading failures.
 */
export class RootErrorBoundary extends Component<RootErrorBoundaryProps, RootErrorBoundaryState> {
  constructor(props: RootErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<RootErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to structured logger (also logs to console)
    logError('[RootErrorBoundary] Application crashed', 'error-boundary', error, {
      componentStack: errorInfo.componentStack,
    });

    // TODO: Send to error reporting service (Sentry, etc.)
    // This would be the place to report to external services
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // Minimal inline styles to avoid dependency on CSS that might have failed
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#0f0f0f',
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            padding: '24px',
          }}
        >
          <div
            style={{
              maxWidth: '500px',
              textAlign: 'center',
            }}
          >
            {/* Error icon */}
            <div
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 24px',
              }}
            >
              <AlertTriangle
                style={{ width: '40px', height: '40px', color: '#ef4444' }}
              />
            </div>

            {/* Title */}
            <h1
              style={{
                fontSize: '24px',
                fontWeight: 'bold',
                marginBottom: '12px',
              }}
            >
              Application Error
            </h1>

            {/* Description */}
            <p
              style={{
                color: '#a1a1aa',
                marginBottom: '24px',
                lineHeight: '1.6',
              }}
            >
              We're sorry, but something went wrong. The application encountered
              an unexpected error and couldn't recover.
            </p>

            {/* Error message */}
            {this.state.error && (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '24px',
                  textAlign: 'left',
                }}
              >
                <p
                  style={{
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    color: '#fca5a5',
                    wordBreak: 'break-word',
                  }}
                >
                  {this.state.error.message}
                </p>
              </div>
            )}

            {/* Action buttons */}
            <div
              style={{
                display: 'flex',
                gap: '12px',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <button
                onClick={this.handleReload}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 24px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                }}
              >
                <RefreshCw style={{ width: '16px', height: '16px' }} />
                Reload Application
              </button>

              <button
                onClick={this.handleGoHome}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  color: 'white',
                  border: '1px solid #3f3f46',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                }}
              >
                Go to Homepage
              </button>
            </div>

            {/* Contact info */}
            <p
              style={{
                marginTop: '32px',
                fontSize: '12px',
                color: '#71717a',
              }}
            >
              If this problem persists, please contact{' '}
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                style={{ color: '#3b82f6', textDecoration: 'underline' }}
              >
                <Mail
                  style={{
                    width: '12px',
                    height: '12px',
                    display: 'inline',
                    verticalAlign: 'middle',
                    marginRight: '4px',
                  }}
                />
                {SUPPORT_EMAIL}
              </a>
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default RootErrorBoundary;
