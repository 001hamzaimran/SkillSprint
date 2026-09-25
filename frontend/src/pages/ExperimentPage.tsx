import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { ArrowLeft, Beaker, RefreshCw, Download, Activity, Clock, ListChecks, ArrowRight } from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
import api from '@/lib/api';
import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';

export default function ExperimentPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchExperiment = async (showToast = false) => {
    if (!id) return;
    try {
      if (showToast) setRefreshing(true);
      const res = await api.get(`experiments/${id}`).json<any>();
      setData(res);
      if (showToast) toast.success('Experiment data refreshed');
    } catch {
      toast.error('Failed to load experiment data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchExperiment();
  }, [id]);

  if (loading) {
    return <div className="p-12 flex justify-center"><Spinner size="lg" /></div>;
  }

  if (!data || !data.experiment) {
    return <EmptyState title="Experiment not found" description="Could not load the requested experiment." />;
  }

  const { experiment, jobs = [], plans = [], comparison } = data;
  const bothCompleted = jobs.length === 2 && jobs.every((j: any) => j && j.status === 'completed');

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <Link to="/plans" className="text-sm text-muted hover:text-ink flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Plans
        </Link>
        <Button 
          variant="secondary" 
          size="sm"
          onClick={() => fetchExperiment(true)}
          disabled={refreshing}
        >
          <RefreshCw className={cn("w-4 h-4 mr-2", refreshing && "animate-spin")} />
          Refresh results
        </Button>
      </div>

      <PageHeader 
        eyebrow="MEASURE REPEATABILITY" 
        title="Controlled consistency run" 
        subtitle="Comparing dual parallel runs to ensure LLM consistency."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {jobs.map((job: any, index: number) => (
          <Card key={job?._id || index} className={cn("border", job?.status === 'failed' ? 'border-red-200' : 'border-border')}>
            <CardHeader className="bg-paper pb-4 border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="w-5 h-5 text-muted" /> Run {index + 1}
                </CardTitle>
                <StatusBadge status={job?.status || 'queued'} />
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted mb-1 flex items-center gap-1"><Clock className="w-3 h-3" /> Created</p>
                  <p className="text-sm font-medium text-ink">{job?.created_at ? formatDateTime(job.created_at) : '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted mb-1">Attempts</p>
                  <p className="text-sm font-medium text-ink">{job?.attempts || 0}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2">
                {job?._id && (
                  <Link to={`/jobs/${job._id}`} className="text-sm font-medium text-green hover:underline">
                    View Job details
                  </Link>
                )}
                {job?.result_id && (
                  <Link to={`/plans/${job.result_id}`} className="text-sm font-medium text-green hover:underline">
                    View generated Plan
                  </Link>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {bothCompleted && comparison ? (
        <div className="space-y-6 mt-8">
          <h3 className="text-xl font-bold text-ink">Consistency Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <StatCard 
              label="Consistency Score" 
              value={comparison.consistency_score !== null ? `${(comparison.consistency_score * 100).toFixed(1)}%` : 'N/A'} 
              subtext={comparison.method}
            />
            
            <div className="flex flex-col gap-3 justify-center">
              <Button 
                variant="secondary" 
                className="w-full justify-start"
                onClick={() => window.open(`/experiments/${id}/json`, '_blank')}
              >
                <Download className="w-4 h-4 mr-2 text-muted" /> Download consistency JSON
              </Button>
              {plans[0]?._id && plans[1]?._id && (
                <Link to={`/plans/${plans[0]._id}/compare?other=${plans[1]._id}`}>
                  <Button className="w-full justify-start bg-green text-white hover:bg-green/90">
                    <ListChecks className="w-4 h-4 mr-2" /> Open detailed comparison <ArrowRight className="w-4 h-4 ml-auto" />
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {comparison.categories && (
            <Card>
              <CardHeader>
                <CardTitle>Categories Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="border border-border rounded-md overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-paper border-b border-border text-muted">
                      <tr>
                        <th className="px-4 py-3 font-medium">Category</th>
                        <th className="px-4 py-3 font-medium">Score</th>
                        <th className="px-4 py-3 font-medium">Overlap</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border bg-white">
                      {comparison.categories.map((cat: any, i: number) => (
                        <tr key={i} className="hover:bg-paper/50">
                          <td className="px-4 py-3 font-medium text-ink">{cat.category}</td>
                          <td className="px-4 py-3">{cat.score !== null ? `${(cat.score * 100).toFixed(0)}%` : '—'}</td>
                          <td className="px-4 py-3">{cat.intersection}/{cat.union}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <div className="mt-8">
          <EmptyState 
            icon={<Beaker className="w-10 h-10 text-muted" />}
            title={!bothCompleted ? "Experiment in progress" : "Comparison pending"} 
            description={!bothCompleted ? "Results will appear here once both runs complete." : "The jobs are done but comparison data is not yet available."} 
          />
        </div>
      )}
    </div>
  );
}
