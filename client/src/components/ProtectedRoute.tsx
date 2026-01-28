import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useAdmin } from '@/hooks/useAdmin';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAuth?: boolean;
  requireAdmin?: boolean;
  redirectTo?: string;
}

/**
 * A route wrapper that protects routes based on authentication and role requirements.
 *
 * @param children - The protected content to render
 * @param requireAuth - If true, user must be authenticated (default: true)
 * @param requireAdmin - If true, user must have admin role
 * @param redirectTo - Where to redirect if not authorized (default: /auth for auth, / for admin)
 *
 * @example
 * // Require authentication
 * <ProtectedRoute>
 *   <Dashboard />
 * </ProtectedRoute>
 *
 * @example
 * // Require admin role
 * <ProtectedRoute requireAdmin>
 *   <AdminPanel />
 * </ProtectedRoute>
 */
export function ProtectedRoute({
  children,
  requireAuth = true,
  requireAdmin = false,
  redirectTo,
}: ProtectedRouteProps) {
  const location = useLocation();
  const { isAuthenticated, authReady, loading: authLoading } = useAuth();
  const { isAdmin, isLoading: adminLoading } = useAdmin();

  // Show loading spinner while auth state is being determined
  // This prevents flash of content or redirect flicker
  if (!authReady || authLoading) {
    return <LoadingSpinner />;
  }

  // Check authentication requirement
  if (requireAuth && !isAuthenticated) {
    // Save the attempted location for redirect after login
    const destination = redirectTo || '/auth';
    return <Navigate to={destination} state={{ from: location }} replace />;
  }

  // If admin is required, wait for admin check to complete
  if (requireAdmin) {
    if (adminLoading) {
      return <LoadingSpinner />;
    }

    if (!isAdmin) {
      // User is authenticated but not admin - redirect to home
      const destination = redirectTo || '/';
      return <Navigate to={destination} replace />;
    }
  }

  // All checks passed, render the protected content
  return <>{children}</>;
}

/**
 * A wrapper specifically for admin-only routes.
 * Combines authentication and admin role requirements.
 */
export function AdminRoute({ children, redirectTo }: Omit<ProtectedRouteProps, 'requireAuth' | 'requireAdmin'>) {
  return (
    <ProtectedRoute requireAuth requireAdmin redirectTo={redirectTo}>
      {children}
    </ProtectedRoute>
  );
}

/**
 * Loading spinner component for auth checks
 */
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );
}

export default ProtectedRoute;
