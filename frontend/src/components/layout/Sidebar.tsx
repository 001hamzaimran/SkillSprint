import { NavLink, useNavigate } from 'react-router';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { EDITORS, REVIEWERS } from '@/types';
import { 
  LayoutDashboard, BookOpen, GraduationCap, ClipboardCheck, 
  Users, Map, ShieldCheck, BarChart3, Settings, LogOut, Activity
} from 'lucide-react';

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) return null;

  const isEditorOrReviewer = EDITORS.has(user.role) || REVIEWERS.has(user.role);
  const isReviewer = REVIEWERS.has(user.role);
  const isManager = user.role === 'manager';
  const isAdmin = user.role === 'admin';
  const isEmployee = user.role === 'employee';

  return (
    <aside className="w-full md:w-[244px] bg-surface border-r border-border md:fixed left-0 top-0 md:h-screen flex flex-col overflow-y-auto shrink-0">
      <div className="p-6">
        <div className="flex items-center gap-2 font-bold text-xl mb-1 text-ink">
          <div className="w-6 h-6 bg-green rounded-full flex items-center justify-center text-white text-sm">s</div>
          <span>SkillSprint <span className="text-muted font-normal text-sm">AI</span></span>
        </div>
        <div className="text-[10px] font-bold text-muted tracking-wider uppercase">
          AsterBridge Workspace
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {[
          { path: '/search', label: 'Search', show: true },
          { path: '/insights', label: 'Progress insights', show: true },
          { path: '/manage', label: 'Manage people & roles', show: EDITORS.has(user.role) },
          { path: '/review-queue', label: 'Review queue', show: isReviewer },
          { path: '/compare', label: 'Compare profiles', show: isEditorOrReviewer },
          { path: '/settings', label: 'Onboarding schedule', show: isAdmin },
        ].filter(item => item.show).map(item => <NavLink key={item.path} to={item.path} className={({ isActive }) => cn('block px-3 py-2 rounded-md text-sm font-medium', isActive ? 'bg-green/10 text-green' : 'text-muted hover:bg-paper')}>{item.label}</NavLink>)}
        <NavLink to="/" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
          <LayoutDashboard className="w-4 h-4" />
          Overview
        </NavLink>
        
        {isEditorOrReviewer && (
          <>
            <NavLink to="/documents" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
              <BookOpen className="w-4 h-4" />
              Knowledge library
            </NavLink>
            <NavLink to="/matrix" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
              <GraduationCap className="w-4 h-4" />
              Role requirements
            </NavLink>
            <NavLink to="/verification" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
              <ShieldCheck className="w-4 h-4" />
              Verification
            </NavLink>
            <NavLink to="/roles" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
              <Settings className="w-4 h-4" />
              Job roles
            </NavLink>
          </>
        )}

        <NavLink to="/employees" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
          <Users className="w-4 h-4" />
          People
        </NavLink>
        
        <NavLink to="/plans" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
          <Map className="w-4 h-4" />
          Onboarding plans
        </NavLink>

        <NavLink to="/learning" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
          <GraduationCap className="w-4 h-4" />
          {isEmployee ? 'My Sprint' : 'Learning progress'}
        </NavLink>

        {(isReviewer || isManager) && (
          <NavLink to="/assessments" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
            <ClipboardCheck className="w-4 h-4" />
            Assessments
          </NavLink>
        )}

        {isReviewer && (
          <NavLink to="/audit" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
            <Activity className="w-4 h-4" />
            Activity trail
          </NavLink>
        )}

        {isAdmin && (
          <NavLink to="/users" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
            <Settings className="w-4 h-4" />
            Access management
          </NavLink>
        )}

        <NavLink to="/reports" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium", isActive ? "bg-green/10 text-green" : "text-muted hover:bg-paper hover:text-ink")}>
          <BarChart3 className="w-4 h-4" />
          Reports
        </NavLink>
      </nav>

      <div className="px-4 py-4 mt-auto">
        <div className="bg-paper p-4 rounded-lg border border-border mb-4">
          <h4 className="text-xs font-bold text-ink uppercase mb-2">Built on evidence</h4>
          <p className="text-xs text-muted mb-2">Every learning journey starts with a trusted source.</p>
          <div className="text-[10px] font-medium text-green">Source &rarr; requirement &rarr; learning</div>
        </div>

        <div className="flex items-center gap-3 mb-4 px-2">
          <div className="w-8 h-8 rounded-full bg-border flex items-center justify-center font-bold text-sm text-ink shrink-0">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="text-sm font-medium truncate text-ink">{user.name}</div>
            <div className="text-xs text-muted truncate capitalize">{user.role.replace('_', ' ')}</div>
          </div>
        </div>
        
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted hover:text-ink rounded-md hover:bg-paper transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
