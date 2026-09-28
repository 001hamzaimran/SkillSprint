import { Link, useLocation } from 'react-router';
import { Search, Sparkles, ChevronRight } from 'lucide-react';

export function Topbar() {
  const { pathname } = useLocation();
  const names: Record<string, string> = { matrix: 'Role requirements', documents: 'Knowledge library', employees: 'People', plans: 'Onboarding plans', learning: 'Learning progress', settings: 'Onboarding schedule', users: 'Access management', manage: 'Manage people & roles', insights: 'Progress insights', 'review-queue': 'Review queue', audit: 'Activity trail' };
  const segment = pathname.split('/')[1];
  const title = names[segment] || segment?.replace(/-/g, ' ') || 'Overview';
  return (
    <header className="min-h-[74px] flex flex-wrap gap-3 items-center justify-between px-4 md:px-8 py-3 border-b border-border bg-white/85">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted hidden sm:inline">Workspace</span><ChevronRight className="w-3 h-3 text-muted hidden sm:block" />
        <span className="font-semibold text-ink capitalize">{title}</span>
      </div>
      <div className="flex items-center gap-2">
        <Link to="/search" className="flex gap-2 items-center rounded-full border border-border bg-white px-3 py-2 text-xs text-muted hover:text-green" aria-label="Search workspace"><Search className="h-4 w-4" /><span className="hidden sm:inline">Search workspace</span></Link>
        <button type="button" onClick={() => window.dispatchEvent(new Event('skillsprint:help'))} className="flex items-center gap-2 px-3 py-2 bg-lime/40 rounded-full text-xs font-semibold text-ink"><Sparkles className="h-4 w-4" />Need a hand?</button>
      </div>
    </header>
  );
}
