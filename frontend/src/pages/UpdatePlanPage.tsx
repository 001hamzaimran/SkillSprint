import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { ArrowLeft, RefreshCw, AlertTriangle, ShieldCheck, FileMinus, FilePlus } from 'lucide-react';
import { usePlanStore } from '@/stores/planStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';
import type { Plan } from '@/types';

interface UpdatePreviewData {
  plan: Plan;
  delta: {
    retained: string[];
    regenerate: string[];
    removed: string[];
    reasons?: Record<string, string>;
  };
  state: {
    unresolved: Array<{ key: string; titles: string[]; values: string[] }>;
    requirements: any[];
  };
  employee: any;
  old: Record<string, any>;
  new: Record<string, any>;
}

export default function UpdatePlanPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentPlan, fetchPlan, fetchUpdatePreview, triggerUpdate } = usePlanStore();
  const [preview, setPreview] = useState<UpdatePreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      fetchPlan(id),
      fetchUpdatePreview(id)
        .then((data) => setPreview(data as unknown as UpdatePreviewData))
        .catch(() => {
          toast.error('Failed to fetch update preview');
        }),
    ]).finally(() => {
      setLoading(false);
    });
  }, [id, fetchPlan, fetchUpdatePreview]);

  const handleUpdate = async () => {
    if (!id) return;
    try {
      setUpdating(true);
      const jobId = await triggerUpdate(id);
      toast.success('Update job enqueued');
      navigate(`/jobs/${jobId}`);
    } catch {
      toast.error('Failed to trigger update');
    } finally {
      setUpdating(false);
    }
  };

  if (loading && !preview) {
    return (
      <div className="p-8 flex justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!currentPlan && !preview) {
    return <EmptyState title="Plan not found" description="Could not load the requested plan." />;
  }

  const hasConflicts = (preview?.state?.unresolved?.length || 0) > 0;
  const retainedCount = preview?.delta?.retained?.length || 0;
  const regenerateCount = preview?.delta?.regenerate?.length || 0;
  const removedCount = preview?.delta?.removed?.length || 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="flex items-center gap-2 text-sm text-muted mb-4">
        <Link to={`/plans/${id}`} className="hover:text-ink flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Plan
        </Link>
      </div>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <PageHeader 
          eyebrow="CHANGE WHAT NEEDS TO CHANGE" 
          title="Selective plan update" 
        />
        
        <Button 
          onClick={handleUpdate} 
          disabled={hasConflicts || updating || !preview}
          className="bg-green text-white hover:bg-green/90 shrink-0"
        >
          {updating ? <Spinner size="sm" className="mr-2 text-white" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Generate affected modules only →
        </Button>
      </div>

      {hasConflicts && (
        <div className="bg-amber/10 border border-amber/20 rounded-md p-4 flex gap-3 text-amber items-start animate-in fade-in">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-sm">Unresolved conflicts</h4>
            <p className="text-sm mt-1">Resolve rule conflicts in the Verification Center before updating.</p>
          </div>
        </div>
      )}

      {preview && (
        <div className="space-y-8 animate-in fade-in duration-300">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard 
              label="Unchanged Retained" 
              value={retainedCount} 
              className="border-green/20 bg-green/5"
            />
            <StatCard 
              label="Modules to Regenerate" 
              value={regenerateCount} 
              className="border-amber/20 bg-amber/5"
            />
            <StatCard 
              label="Requirements Removed" 
              value={removedCount} 
              className="border-red-200 bg-red-50"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1 shadow-sm h-fit">
              <CardHeader className="pb-3 border-b border-border bg-paper/50">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-green" /> Retained ({retainedCount})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-border">
                  {preview.delta.retained?.map((reqId: string, i: number) => {
                    const req = preview.new?.[reqId] || preview.old?.[reqId];
                    return (
                      <li key={i} className="p-4 text-sm text-ink">
                        <div className="font-medium">{req?.title || reqId}</div>
                        <div className="text-xs text-muted font-mono">{reqId}</div>
                      </li>
                    );
                  })}
                  {retainedCount === 0 && (
                    <li className="p-4 text-sm text-muted text-center">No retained requirements</li>
                  )}
                </ul>
              </CardContent>
            </Card>

            <Card className="lg:col-span-1 shadow-sm h-fit border-amber/20">
              <CardHeader className="pb-3 border-b border-border bg-amber/5">
                <CardTitle className="text-base flex items-center gap-2">
                  <FilePlus className="w-4 h-4 text-amber" /> Needing Regeneration ({regenerateCount})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-border">
                  {preview.delta.regenerate?.map((reqId: string, i: number) => {
                    const req = preview.new?.[reqId];
                    const reason = preview.delta.reasons?.[reqId];
                    return (
                      <li key={i} className="p-4">
                        <p className="text-sm font-medium text-ink">{req?.title || reqId}</p>
                        <p className="text-xs text-muted font-mono">{reqId}</p>
                        {reason && <p className="text-xs text-amber mt-1 font-medium">{reason}</p>}
                      </li>
                    );
                  })}
                  {regenerateCount === 0 && (
                    <li className="p-4 text-sm text-muted text-center">No modules need regeneration</li>
                  )}
                </ul>
              </CardContent>
            </Card>

            <Card className="lg:col-span-1 shadow-sm h-fit border-red-200">
              <CardHeader className="pb-3 border-b border-border bg-red-50/50">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileMinus className="w-4 h-4 text-red-500" /> Removed ({removedCount})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-border">
                  {preview.delta.removed?.map((reqId: string, i: number) => {
                    const req = preview.old?.[reqId];
                    return (
                      <li key={i} className="p-4 text-sm text-ink line-through opacity-70">
                        <div>{req?.title || reqId}</div>
                        <div className="text-xs text-muted font-mono">{reqId}</div>
                      </li>
                    );
                  })}
                  {removedCount === 0 && (
                    <li className="p-4 text-sm text-muted text-center">No requirements removed</li>
                  )}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
