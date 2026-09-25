import { Navigate, Outlet, useLocation } from 'react-router';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  children?: React.ReactNode;
}

export function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const { user, isInitialized } = useAuthStore();
  const location = useLocation();

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <div className="w-8 h-8 border-4 border-green border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-paper">
        <h1 className="text-2xl font-bold mb-2 text-ink">403 - Forbidden</h1>
        <p className="text-muted">You do not have permission to access this page.</p>
      </div>
    );
  }

  return children ? <>{children}</> : <Outlet />;
}
