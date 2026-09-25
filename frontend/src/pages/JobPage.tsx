import { useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { toast } from 'sonner';
import { ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { useJobStore } from '@/stores/jobStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/shared/StatusBadge';

export function JobPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentJob: job, isLoading: loading, fetchJob, startPolling, stopPolling } = useJobStore();

  useEffect(() => {
    if (id) {
      fetchJob(id).then(() => {
        const j = useJobStore.getState().currentJob;
        if (j?.status === 'queued' || j?.status === 'running') {
          startPolling(id, (completedJob) => {
            toast.success('Job completed successfully');
            if (completedJob.result_id) {
              if (completedJob.kind === 'extract') {
                navigate(`/documents/${completedJob.target_id}`);
              } else {
                navigate(`/plans/${completedJob.result_id}`);
              }
            }
          });
        }
      }).catch(() => toast.error('Failed to fetch job'));
    }

    return () => {
      stopPolling();
    };
  }, [id, fetchJob, startPolling, stopPolling, navigate]);

  if (loading && !job) {
    return (
      <div className="flex justify-center p-16">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="container mx-auto p-6 max-w-2xl text-center mt-10 space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h2 className="text-2xl font-bold text-ink">Job not found</h2>
        <p className="text-muted">The requested job could not be found or an error occurred.</p>
        <Link to="/">
          <Button variant="secondary">Go home</Button>
        </Link>
      </div>
    );
  }

  const isRunning = job.status === 'queued' || job.status === 'running';
  const isFailed = job.status === 'failed';
  const isCompleted = job.status === 'completed';

  const jobTitle = job.kind === 'generate' ? 'Generating Plan' : 
                   job.kind === 'extract' ? 'Extracting Requirements' : 
                   job.kind === 'selective' ? 'Updating Plan Modules' : 
                   'Background Job';

  return (
    <div className="container mx-auto p-6 max-w-3xl space-y-8">
      <PageHeader
        eyebrow="WORK IN PROGRESS"
        title={jobTitle}
        subtitle={`Job ID: ${job._id}`}
      />

      <div className="bg-white border border-border rounded-xl p-8 shadow-sm text-center space-y-6">
        <div className="flex justify-center">
          <StatusBadge status={job.status} />
        </div>

        {isRunning && (
          <div className="space-y-4 py-8">
            <Spinner size="lg" className="mx-auto" />
            <h3 className="text-xl font-semibold text-ink">Processing request...</h3>
            <p className="text-muted max-w-md mx-auto">
              Your request is running in the background. Larger documents and plans can take several minutes. Generated content will still need human review.
            </p>
          </div>
        )}

        {isFailed && (
          <div className="space-y-4 py-6">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto" />
            <h3 className="text-xl font-semibold text-ink">Job Failed</h3>
            <p className="text-red-600 bg-red-50 p-4 rounded-lg border border-red-200 max-w-lg mx-auto font-mono text-sm">
              {job.error || 'An unexpected error occurred during execution.'}
            </p>
          </div>
        )}

        {isCompleted && (
          <div className="space-y-4 py-6">
            <CheckCircle className="w-16 h-16 text-green mx-auto" />
            <div>
              <h3 className="text-xl font-semibold text-ink mb-2">Job Completed Successfully</h3>
              <p className="text-muted mb-6">
                The {job.kind} task has finished processing.
              </p>
              
              {job.kind === 'extract' ? (
                <Link to={`/documents/${job.target_id}`}>
                  <Button className="gap-2 bg-green text-white hover:bg-green/90">
                    View Document <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              ) : (
                <Link to={`/plans/${job.result_id || job.target_id}`}>
                  <Button className="gap-2 bg-green text-white hover:bg-green/90">
                    Open Result Plan <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default JobPage;
