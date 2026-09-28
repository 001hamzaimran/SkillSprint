import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { PageErrorBoundary } from './PageErrorBoundary';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useAuthStore } from '@/stores/authStore';
import { useUIStore } from '@/stores/uiStore';

export function AppShell() {
  const location = useLocation();
  const { fetchMe, isInitialized } = useAuthStore();
  const { flashMessage } = useUIStore();

  useEffect(() => {
    if (!isInitialized) {
      fetchMe();
    }
  }, [fetchMe, isInitialized]);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <div className="w-8 h-8 border-4 border-green border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper flex flex-col md:flex-row text-ink">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col md:ml-[244px]">
        <Topbar />
        <main className="flex-1">
          {flashMessage && (
            <div className="bg-amber/10 text-amber px-8 py-3 text-sm font-medium border-b border-amber/20">
              {flashMessage}
            </div>
          )}
          <div className="max-w-[1550px] mx-auto px-4 md:px-[38px] py-6 md:py-9 overflow-x-auto">
            <PageErrorBoundary key={location.key}>
              <Outlet />
            </PageErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
