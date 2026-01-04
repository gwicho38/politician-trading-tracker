import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary, withErrorBoundary } from './ErrorBoundary';

// Component that throws an error
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Content rendered successfully</div>;
}

// Suppress console.error during tests
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  describe('normal rendering', () => {
    it('should render children when there is no error', () => {
      render(
        <ErrorBoundary>
          <div>Test Content</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should render multiple children', () => {
      render(
        <ErrorBoundary>
          <div>Child 1</div>
          <div>Child 2</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('Child 1')).toBeInTheDocument();
      expect(screen.getByText('Child 2')).toBeInTheDocument();
    });
  });

  describe('error catching', () => {
    it('should catch errors and show error fallback', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });

    it('should show section name in error message when provided', () => {
      render(
        <ErrorBoundary name="Dashboard">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText(/The Dashboard section/)).toBeInTheDocument();
    });

    it('should call onError callback when error is caught', () => {
      const onError = vi.fn();

      render(
        <ErrorBoundary onError={onError}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: 'Test error message' }),
        expect.objectContaining({ componentStack: expect.any(String) })
      );
    });

    it('should log error to console', () => {
      render(
        <ErrorBoundary name="TestSection">
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('[ErrorBoundary:TestSection]'),
        expect.any(Error)
      );
    });
  });

  describe('minimal fallback', () => {
    it('should show minimal error UI when minimal prop is true', () => {
      render(
        <ErrorBoundary minimal>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Error loading content')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      // Should NOT show the full error card
      expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
    });
  });

  describe('custom fallback', () => {
    it('should render custom fallback when provided', () => {
      render(
        <ErrorBoundary fallback={<div>Custom Error UI</div>}>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
      expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
    });
  });

  describe('reset functionality', () => {
    it('should reset error state when Try Again is clicked', () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      // Error should be shown
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Rerender with non-throwing component before clicking retry
      rerender(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </ErrorBoundary>
      );

      // Click try again
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));

      // Content should now be visible
      expect(screen.getByText('Content rendered successfully')).toBeInTheDocument();
    });

    it('should have Go Home button that navigates to home', () => {
      // Mock window.location
      const originalLocation = window.location;
      Object.defineProperty(window, 'location', {
        value: { href: '' },
        writable: true,
      });

      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      const homeButton = screen.getByRole('button', { name: /go home/i });
      fireEvent.click(homeButton);

      expect(window.location.href).toBe('/');

      // Restore
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true,
      });
    });
  });

  describe('resetKeys', () => {
    it('should auto-reset when resetKeys change', () => {
      const { rerender } = render(
        <ErrorBoundary resetKeys={['key1']}>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      // Error should be shown
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Change the children to not throw and update resetKeys
      rerender(
        <ErrorBoundary resetKeys={['key2']}>
          <ThrowingComponent shouldThrow={false} />
        </ErrorBoundary>
      );

      // Error should be cleared and content shown
      expect(screen.getByText('Content rendered successfully')).toBeInTheDocument();
    });

    it('should not reset when resetKeys stay the same', () => {
      const { rerender } = render(
        <ErrorBoundary resetKeys={['key1']}>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Rerender with same keys but different children
      rerender(
        <ErrorBoundary resetKeys={['key1']}>
          <ThrowingComponent shouldThrow={false} />
        </ErrorBoundary>
      );

      // Should still show error (keys didn't change)
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });
  });
});

describe('withErrorBoundary HOC', () => {
  it('should wrap component with error boundary', () => {
    const MyComponent = () => <div>My Component</div>;
    const WrappedComponent = withErrorBoundary(MyComponent);

    render(<WrappedComponent />);

    expect(screen.getByText('My Component')).toBeInTheDocument();
  });

  it('should catch errors in wrapped component', () => {
    const WrappedThrowing = withErrorBoundary(ThrowingComponent);

    render(<WrappedThrowing />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should pass options to error boundary', () => {
    const onError = vi.fn();
    const WrappedThrowing = withErrorBoundary(ThrowingComponent, {
      onError,
      name: 'WrappedSection',
    });

    render(<WrappedThrowing />);

    expect(onError).toHaveBeenCalled();
    expect(screen.getByText(/The WrappedSection section/)).toBeInTheDocument();
  });

  it('should have correct displayName', () => {
    function NamedComponent() {
      return <div>Named</div>;
    }
    const Wrapped = withErrorBoundary(NamedComponent);

    expect(Wrapped.displayName).toBe('withErrorBoundary(NamedComponent)');
  });
});
