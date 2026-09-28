import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { EDITORS, REVIEWERS } from '@/types';
import {
  LayoutDashboard, BookOpen, GraduationCap, ClipboardCheck, Users, Map,
  ShieldCheck, BarChart3, Settings, LogOut, Activity, Search, TrendingUp,
  UsersRound, ListChecks, GitCompareArrows, CalendarDays, BriefcaseBusiness,
  Menu, X, type LucideIcon,
} from 'lucide-react';

type NavigationItem = { path: string; label: string; icon: LucideIcon; show: boolean };

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  if (!user) return null;

  const editor = EDITORS.has(user.role);
  const reviewer = REVIEWERS.has(user.role);
  const sourceAccess = editor || reviewer;
  const admin = user.role === 'admin';
  const groups: { title: string; items: NavigationItem[] }[] = [
    {
      title: 'Workspace',
      items: [
        { path: '/', label: 'Overview', icon: LayoutDashboard, show: true },
        { path: '/documents', label: 'Knowledge library', icon: BookOpen, show: sourceAccess },
        { path: '/matrix', label: 'Role requirements', icon: GraduationCap, show: sourceAccess },
        { path: '/verification', label: 'Verification', icon: ShieldCheck, show: sourceAccess },
        { path: '/roles', label: 'Job roles', icon: BriefcaseBusiness, show: sourceAccess },
        { path: '/employees', label: 'People', icon: Users, show: true },
        { path: '/plans', label: 'Onboarding plans', icon: Map, show: true },
        { path: '/learning', label: user.role === 'employee' ? 'My Sprint' : 'Learning progress', icon: GraduationCap, show: true },
        { path: '/assessments', label: 'Assessments', icon: ClipboardCheck, show: reviewer || user.role === 'manager' },
        { path: '/reports', label: 'Reports', icon: BarChart3, show: true },
      ],
    },
    {
      title: 'Tools & insights',
      items: [
        { path: '/search', label: 'Search', icon: Search, show: true },
        { path: '/insights', label: 'Progress insights', icon: TrendingUp, show: true },
        { path: '/review-queue', label: 'Review queue', icon: ListChecks, show: reviewer },
        { path: '/compare', label: 'Compare profiles', icon: GitCompareArrows, show: sourceAccess },
      ],
    },
    {
      title: 'Administration',
      items: [
        { path: '/manage', label: 'Manage people & roles', icon: UsersRound, show: editor },
        { path: '/settings', label: 'Onboarding schedule', icon: CalendarDays, show: admin },
        { path: '/users', label: 'Access management', icon: Settings, show: admin },
        { path: '/audit', label: 'Activity trail', icon: Activity, show: reviewer },
      ],
    },
  ];

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <aside className="w-full md:w-[244px] bg-surface border-b md:border-b-0 md:border-r border-border md:fixed left-0 top-0 md:h-dvh flex flex-col shrink-0 md:z-20">
      <div className="px-5 py-5 shrink-0 flex items-center justify-between border-b border-border">
        <div>
          <div className="flex items-center gap-2 font-bold text-xl text-ink">
            <span className="w-7 h-7 bg-green rounded-lg flex items-center justify-center text-white text-sm">s</span>
            <span>SkillSprint <span className="text-muted font-normal text-sm">AI</span></span>
          </div>
          <p className="mt-2 text-[10px] font-semibold text-muted tracking-widest uppercase">AsterBridge Workspace</p>
        </div>
        <button type="button" className="md:hidden p-2 rounded-md hover:bg-paper" aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={mobileOpen} aria-controls="workspace-navigation" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      <nav id="workspace-navigation" aria-label="Main navigation" className={cn('min-h-0 flex-1 overflow-y-auto px-3 py-4 space-y-5 sidebar-scroll', mobileOpen ? 'block max-h-[60dvh] md:max-h-none' : 'hidden md:block')}>
        {groups.map(group => {
          const items = group.items.filter(item => item.show);
          if (!items.length) return null;
          return (
            <section key={group.title} aria-label={group.title}>
              <h2 className="px-3 mb-2 text-[10px] uppercase tracking-widest font-semibold text-muted">{group.title}</h2>
              <div className="space-y-1">
                {items.map(({ path, label, icon: Icon }) => (
                  <NavLink key={path} to={path} end={path === '/'} onClick={() => setMobileOpen(false)} className={({ isActive }) => cn('flex items-center gap-3 min-h-10 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors', isActive ? 'bg-green/10 text-green font-semibold' : 'text-muted hover:bg-paper hover:text-ink')}>
                    <Icon aria-hidden="true" className="w-4 h-4 shrink-0" />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </section>
          );
        })}
      </nav>

      <div className={cn('shrink-0 border-t border-border p-3 bg-surface', mobileOpen ? 'block' : 'hidden md:block')}>
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-green/10 flex items-center justify-center font-semibold text-sm text-green shrink-0">{user.name.charAt(0).toUpperCase()}</div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium truncate text-ink">{user.name}</div>
            <div className="text-xs text-muted truncate capitalize">{user.role.replace(/_/g, ' ')}</div>
          </div>
        </div>
        <button type="button" onClick={handleLogout} className="w-full flex items-center gap-3 px-3 py-2 text-sm text-muted hover:text-ink rounded-lg hover:bg-paper transition-colors">
          <LogOut aria-hidden="true" className="w-4 h-4" /> Sign out
        </button>
      </div>
    </aside>
  );
}
