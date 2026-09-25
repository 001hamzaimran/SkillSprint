import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router';
import { toast } from 'sonner';
import { ArrowUpRight, FileText, Plus } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { usePlanStore } from '@/stores/planStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export function PlansPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { plans, isLoading: loading, fetchPlans } = usePlanStore();
  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';

  useEffect(() => {
    fetchPlans().catch(() => toast.error('Failed to load plans'));
  }, [fetchPlans]);

  if (loading && plans.length === 0) {
    return <Spinner className="mx-auto mt-20" size="lg" />;
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHeader 
          eyebrow="PERSONAL PATHS FORWARD" 
          title="Onboarding plans" 
        />
        {isEditor && (
          <Link to="/employees">
            <Button className="gap-2">
              <Plus className="w-4 h-4" /> Generate a plan
            </Button>
          </Link>
        )}
      </div>

      {plans.length === 0 ? (
        <EmptyState 
          title="No plans found" 
          description="Generate onboarding plans for employees to see them here." 
          icon={<FileText className="w-10 h-10 text-muted" />} 
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {plans.map(plan => {
            const itemCount = plan.content?.items?.length || 0;
            return (
              <Link 
                key={plan._id} 
                to={`/plans/${plan._id}`}
                className="group flex flex-col p-5 bg-white border border-border rounded-xl shadow-sm hover:shadow-md hover:border-green/50 transition-all cursor-pointer relative"
              >
                <div className="absolute top-5 right-5 text-muted group-hover:text-green transition-colors">
                  <ArrowUpRight className="w-5 h-5" />
                </div>
                
                <div className="mb-4">
                  <Badge variant={plan.status === 'Published' ? 'success' : 'default'} className={cn(
                    plan.status === 'Published' ? 'bg-green text-white hover:bg-green/90' : 'bg-paper text-muted'
                  )}>
                    {plan.status || 'Draft'}
                  </Badge>
                </div>
                
                <h3 className="font-semibold text-lg text-ink line-clamp-2 mb-1 group-hover:text-green transition-colors">
                  {plan.content?.title || 'Untitled Plan'}
                </h3>
                <p className="text-sm text-muted mb-6">
                  Employee: {plan.employee_id}
                </p>
                
                <div className="mt-auto pt-4 border-t border-border flex items-center justify-between text-xs text-muted font-medium">
                  <div>Coverage: {Math.round(plan.validation?.coverage || 0)}%</div>
                  <div>{itemCount} items</div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PlansPage;

