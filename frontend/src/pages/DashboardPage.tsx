import React, { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { useAuthStore } from '@/stores/authStore';
import api from '@/lib/api';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Spinner } from '@/components/shared/Spinner';
import { Users, FileText, CheckSquare, BookOpen, ArrowRight, AlertTriangle } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { toast } from 'sonner';

interface DashboardData {
  stats: {
    people_count: number;
    documents_count: number;
    approved_requirements: number;
    generated_plans: number;
  };
  recent_plans: Array<{
    id: string;
    title: string;
    created_at: string;
    status: string;
  }>;
  ai_ready: boolean;
}

function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        setIsLoading(true);
        const result = await api.get('dashboard').json<{
          stats: { employees: number; documents?: number; approved?: number; plans: number };
          plans: Array<{ _id: string; content: { title: string }; created_at: string; status: string }>;
          ai_ready: boolean;
        }>();
        setData({
          ai_ready: result.ai_ready,
          stats: {
            people_count: result.stats.employees,
            documents_count: result.stats.documents ?? 0,
            approved_requirements: result.stats.approved ?? 0,
            generated_plans: result.stats.plans,
          },
          recent_plans: result.plans.map(plan => ({
            id: plan._id, title: plan.content.title,
            created_at: plan.created_at, status: plan.status,
          })),
        });
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard data');
        toast.error('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    }
    fetch();
  }, []);

  return { data, isLoading, error };
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data, isLoading, error } = useDashboardData();

  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="w-8 h-8 text-green" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center text-amber">
        <p>Error loading dashboard. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      <div className="flex flex-wrap gap-4 items-start justify-between">
        <PageHeader 
          eyebrow="THE BIG PICTURE"
          title="A better first chapter."
          subtitle={`Welcome back, ${user?.name || 'User'}`}
        />
        {isEditor && (
          <Button asChild className="bg-green hover:bg-green/90 text-white">
            <Link to="/documents">+ Add company knowledge</Link>
          </Button>
        )}
      </div>

      {!data.ai_ready && (
        <div className="bg-amber/10 border border-amber/20 rounded-xl p-4 flex items-center gap-3 text-amber">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p className="text-sm font-medium">AI generation needs an API key to function. Please contact the administrator.</p>
        </div>
      )}

      {/* Hero Banner */}
      <div className="sprint-hero rounded-3xl p-7 lg:p-10 relative overflow-hidden flex items-center gap-6">
        <div className="relative z-10 max-w-xl flex-1">
          <p className="text-lime text-[10px] font-semibold tracking-[0.22em] uppercase mb-4">From day one to what’s next</p>
          <h2 className="text-3xl lg:text-[40px] leading-tight font-semibold tracking-tight text-white mb-4">Good knowledge.<br /><span className="text-lime">Great beginnings.</span></h2>
          <p className="text-white/80 mb-7 text-sm max-w-md leading-relaxed">
            Turn your company’s knowledge into clear learning paths. Grounded in evidence. Built around your people.
          </p>
          <Button asChild className="bg-lime hover:bg-white text-ink rounded-full px-6">
            <Link to={isEditor ? "/matrix" : "/plans"}>
              {isEditor ? "Explore role requirements" : "Explore your plans"} <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
          </Button>
        </div>
        <div aria-hidden="true" className="sprint-orbit hidden xl:flex w-[270px] h-[250px] shrink-0 items-center justify-center relative">
          <div className="absolute top-4 left-1 rounded-2xl bg-white/10 border border-white/20 px-4 py-3 text-white text-xs flex items-center gap-2 -rotate-6"><FileText className="w-4 h-4 text-lime" />Trusted knowledge</div>
          <div className="w-24 h-24 rounded-3xl bg-lime flex items-center justify-center shadow-xl rotate-6"><BookOpen className="w-11 h-11 text-ink -rotate-6" strokeWidth={1.5} /></div>
          <div className="absolute bottom-3 right-0 rounded-2xl bg-white px-4 py-3 text-ink text-xs flex items-center gap-2 rotate-3 shadow-lg"><CheckSquare className="w-4 h-4 text-green" />A confident next step</div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'People', value: data.stats.people_count, icon: Users, color: 'text-blue-600', bg: 'bg-blue-100' },
          { label: 'Documents', value: data.stats.documents_count, icon: FileText, color: 'text-purple-600', bg: 'bg-purple-100' },
          { label: 'Approved Requirements', value: data.stats.approved_requirements, icon: CheckSquare, color: 'text-green', bg: 'bg-green/10' },
          { label: 'Generated Plans', value: data.stats.generated_plans, icon: BookOpen, color: 'text-amber', bg: 'bg-amber/10' },
        ].map((stat, i) => (
          <div key={i} className="bg-white rounded-2xl border border-border p-5 shadow-[0_4px_24px_-12px_rgba(18,62,55,0.18)]">
            <div className="flex items-center gap-4">
              <div className={cn("p-3 rounded-lg", stat.bg)}>
                <stat.icon className={cn("w-6 h-6", stat.color)} />
              </div>
              <div>
                <p className="text-sm font-medium text-muted">{stat.label}</p>
                <p className="text-2xl font-bold text-ink">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Plans */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-lg font-bold text-ink">Recent learning plans</h3>
          <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
            {data.recent_plans.length === 0 ? (
              <div className="p-8 text-center text-muted">No recent plans found.</div>
            ) : (
              <div className="divide-y divide-border">
                {data.recent_plans.map(plan => (
                  <Link 
                    key={plan.id} 
                    to={`/plans/${plan.id}`}
                    className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-paper flex items-center justify-center group-hover:bg-white group-hover:shadow-sm transition-all border border-border">
                        <BookOpen className="w-5 h-5 text-muted group-hover:text-ink" />
                      </div>
                      <div>
                        <p className="font-medium text-ink">{plan.title}</p>
                        <p className="text-sm text-muted">{formatDate(plan.created_at)}</p>
                      </div>
                    </div>
                    <StatusBadge status={plan.status as any} />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Checklist */}
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-ink">Build on a solid foundation</h3>
          <div className="bg-white border border-border rounded-xl shadow-sm p-6 space-y-6">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green/10 text-green flex items-center justify-center font-bold text-sm">1</div>
              <div>
                <h4 className="font-medium text-ink mb-1">Upload knowledge</h4>
                <p className="text-sm text-muted leading-relaxed">Add policies, procedures, and manuals to the library.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green/10 text-green flex items-center justify-center font-bold text-sm">2</div>
              <div>
                <h4 className="font-medium text-ink mb-1">Extract requirements</h4>
                <p className="text-sm text-muted leading-relaxed">Let AI identify key training mandates and expectations.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green/10 text-green flex items-center justify-center font-bold text-sm">3</div>
              <div>
                <h4 className="font-medium text-ink mb-1">Generate plans</h4>
                <p className="text-sm text-muted leading-relaxed">Create personalized learning paths for your team.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
