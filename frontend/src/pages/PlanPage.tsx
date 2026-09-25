import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import { toast } from 'sonner';
import { ArrowLeft, RefreshCw, CheckCircle2, AlertTriangle, FileJson, History, MessageSquare, Download } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { usePlanStore } from '@/stores/planStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { formatDate, formatDateTime, cn } from '@/lib/utils';
import api from '@/lib/api';

export function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { 
    currentPlan: plan, 
    currentEmployee: employee, 
    fresh, 
    teaching, 
    decisions, 
    isLoading: loading, 
    fetchPlan, 
    reviewPlan, 
    regeneratePlan, 
    runConsistency 
  } = usePlanStore();
  
  const [reviewDecision, setReviewDecision] = useState('comment');
  const [reviewComment, setReviewComment] = useState('');
  const [reviewConfirm, setReviewConfirm] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);

  const isReviewer = user?.role === 'reviewer' || user?.role === 'admin';
  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';

  useEffect(() => {
    if (id) {
      fetchPlan(id).catch(() => toast.error('Failed to load plan'));
    }
  }, [id, fetchPlan]);

  const handleRegenerate = async () => {
    if (!id) return;
    try {
      const jobId = await regeneratePlan(id);
      toast.success('Regeneration started');
      navigate(`/jobs/${jobId}`);
    } catch {
      toast.error('Failed to start regeneration');
    }
  };

  const handleConsistency = async () => {
    if (!id) return;
    try {
      const expId = await runConsistency(id);
      toast.success('Consistency experiment started');
      navigate(`/experiments/${expId}`);
    } catch {
      toast.error('Failed to run consistency check');
    }
  };

  const handleSubmitReview = async () => {
    if (!id || !reviewComment.trim()) return;
    if ((reviewDecision === 'approve' || reviewDecision === 'reject') && !reviewConfirm) {
      toast.error('Please confirm your decision');
      return;
    }
    
    setSubmittingReview(true);
    try {
      await reviewPlan(id, { decision: reviewDecision, comment: reviewComment, confirmed: String(reviewConfirm) });
      toast.success('Review submitted');
      setReviewComment('');
      setReviewConfirm(false);
      fetchPlan(id);
    } catch {
      toast.error('Failed to submit review');
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading || !plan) {
    return <Spinner className="mx-auto mt-20" size="lg" />;
  }

  const employeeName = employee?.name || 'Employee';
  const roleName = employee?.role_name || 'Role';
  const title = plan.content?.title || 'Onboarding Plan';
  const items = plan.content?.items || [];
  const findingsCount = plan.validation?.findings?.length || 0;

  return (
    <div className="container mx-auto p-6 space-y-8">
      <Link to="/plans" className="inline-flex items-center text-sm font-medium text-muted hover:text-ink">
        <ArrowLeft className="w-4 h-4 mr-1" /> Onboarding plans
      </Link>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <PageHeader 
          eyebrow={`${employeeName} · ${roleName}`} 
          title={title} 
          subtitle={plan.content?.summary}
        />
        <a 
          href={`/plans/${id}/json`}
          target="_blank"
          rel="noreferrer"
          download
          className="inline-flex items-center gap-2 text-sm font-medium text-green hover:underline shrink-0 px-4 py-2 border border-border rounded-md bg-paper hover:bg-white transition-colors"
        >
          <Download className="w-4 h-4" /> Download JSON
        </a>
      </div>

      {/* Validation Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-border shadow-sm">
          <span className="text-xs uppercase tracking-wider font-semibold text-muted">Requirements Coverage</span>
          <div className="text-3xl font-bold text-ink mt-2">{plan.validation?.coverage || 0}%</div>
          <span className="text-xs text-muted mt-1 block">Baseline requirement match</span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-border shadow-sm">
          <span className="text-xs uppercase tracking-wider font-semibold text-muted">Traceability Score</span>
          <div className="text-3xl font-bold text-ink mt-2">{plan.validation?.traceability || 0}%</div>
          <span className="text-xs text-muted mt-1 block">Verified to source evidence</span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-border shadow-sm">
          <span className="text-xs uppercase tracking-wider font-semibold text-muted">Validation Findings</span>
          <div className="text-3xl font-bold text-ink mt-2">{findingsCount}</div>
          <span className="text-xs text-muted mt-1 block">
            {findingsCount === 0 ? 'All validation checks passed' : 'Items needing review'}
          </span>
        </div>
      </div>

      {findingsCount > 0 && (
        <div className="bg-amber/10 border border-amber/30 rounded-xl p-6">
          <div className="flex items-center gap-2 text-amber font-semibold mb-2">
            <AlertTriangle className="w-5 h-5" />
            <span>Validation Findings ({findingsCount})</span>
          </div>
          <ul className="space-y-2 mt-3">
            {plan.validation.findings.map((f, i) => (
              <li key={i} className="text-sm text-ink bg-white/60 p-3 rounded border border-amber/20">
                <span className="font-mono text-xs font-bold text-muted mr-2">{f.code}</span>
                {f.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Plan Review Panel */}
      <div className="bg-paper border border-border rounded-xl overflow-hidden">
        <div className="p-4 border-b border-border bg-white flex items-center justify-between">
          <h2 className="font-semibold text-lg flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-muted" /> Plan Review
          </h2>
          <StatusBadge status={plan.status} />
        </div>
        
        <div className="p-5 space-y-6">
          {!fresh && (
            <div className="flex items-center gap-2 text-sm text-amber bg-amber/10 p-3 rounded-md border border-amber/20">
              <AlertTriangle className="w-4 h-4" /> Warning: Source documents have been updated since this plan was generated.
            </div>
          )}

          {teaching && !teaching.passed && teaching.findings.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-md border border-red-200">
              <AlertTriangle className="w-4 h-4" /> Teaching check warnings detected: {teaching.findings.join('; ')}
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <Link to={`/learning/${id}`}>
              <Button variant="secondary" className="gap-2"><FileJson className="w-4 h-4" /> View learning →</Button>
            </Link>
            {(isEditor || isReviewer) && (
              <Button variant="secondary" onClick={handleRegenerate} className="gap-2">
                <RefreshCw className="w-4 h-4" /> Regenerate
              </Button>
            )}
          </div>

          {isReviewer && plan.status !== 'Published' && (
            <div className="bg-white p-5 rounded-lg border border-border mt-6">
              <h3 className="font-medium mb-4">Submit Review</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Decision</Label>
                    <select 
                      value={reviewDecision}
                      onChange={(e) => setReviewDecision(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
                    >
                      <option value="comment">Comment Only</option>
                      <option value="approve">Approve</option>
                      <option value="reject">Reject / Request Changes</option>
                    </select>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Comments</Label>
                  <Textarea 
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    placeholder="Provide feedback on this onboarding plan..."
                    rows={3}
                  />
                </div>

                {(reviewDecision === 'approve' || reviewDecision === 'reject') && (
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={reviewConfirm}
                      onChange={(e) => setReviewConfirm(e.target.checked)}
                      className="rounded border-gray-300 text-green focus:ring-green"
                    />
                    <span className="text-sm font-medium">
                      I confirm my decision to {reviewDecision} this plan.
                    </span>
                  </label>
                )}

                <Button onClick={handleSubmitReview} disabled={submittingReview || !reviewComment.trim()} className="bg-green text-white hover:bg-green/90">
                  {submittingReview ? 'Submitting...' : 'Submit Review'}
                </Button>
              </div>
            </div>
          )}

          {decisions && decisions.length > 0 && (
            <div className="mt-8">
              <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-4 flex items-center gap-2">
                <History className="w-4 h-4" /> Review History
              </h3>
              <div className="space-y-4">
                {decisions.map((rev, idx) => (
                  <div key={idx} className="bg-white p-4 rounded-lg border border-border text-sm">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-ink flex items-center gap-2">
                        {rev.actor_name || 'Reviewer'}
                        <Badge variant={rev.decision === 'approve' ? 'success' : rev.decision === 'reject' ? 'destructive' : 'default'}>
                          {rev.decision}
                        </Badge>
                      </div>
                      <div className="text-muted">{formatDateTime(rev.created_at)}</div>
                    </div>
                    <p className="text-ink whitespace-pre-wrap">{rev.comment}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-4 pt-4 border-t border-border text-sm">
            <Link to={`/plans/${id}/compare`} className="text-green hover:underline">Compare versions</Link>
            <a href={`/plans/${id}/validation.csv`} className="text-green hover:underline" download>Validation CSV</a>
            <Link to={`/plans/${id}/update`} className="text-green hover:underline">Preview update</Link>
            <button onClick={handleConsistency} className="text-green hover:underline font-medium">Run consistency check</button>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-semibold text-ink border-b border-border pb-2">Learning Modules ({items.length})</h2>
          
          <div className="space-y-4">
            {items.map((item, iIdx) => (
              <div key={iIdx} className="bg-white p-5 rounded-lg border border-border shadow-sm space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <Badge variant="default" className="mr-2">{item.stage}</Badge>
                    <Badge variant={item.mandatory ? 'warning' : 'default'}>
                      {item.mandatory ? 'Mandatory' : 'Optional'}
                    </Badge>
                    <h4 className="font-semibold text-ink text-lg mt-2">{item.module_title}</h4>
                    <p className="text-sm text-muted">{item.learning_objective}</p>
                  </div>
                  {(isEditor || isReviewer) && (
                    <Link to={`/plans/${id}/items/${item.requirement_id}/edit`}>
                      <Button variant="secondary" size="sm">Edit module</Button>
                    </Link>
                  )}
                </div>
                
                <p className="text-sm text-ink line-clamp-3">{item.lesson}</p>
                
                {item.checklist && item.checklist.length > 0 && (
                  <div className="text-xs text-muted">
                    <span className="font-semibold text-ink">Checklist: </span>
                    {item.checklist.length} items
                  </div>
                )}

                {item.quiz && (
                  <div className="text-xs text-muted">
                    <span className="font-semibold text-ink">Quiz: </span>
                    {item.quiz.question}
                  </div>
                )}

                {item.source_quote && (
                  <blockquote className="border-l-2 border-green pl-3 py-1 text-xs italic text-muted">
                    "{item.source_quote}"
                  </blockquote>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-ink border-b border-border pb-2">Validation Details</h2>
          
          <div className="bg-white p-5 rounded-lg border border-border shadow-sm space-y-4">
            <h3 className="font-medium text-ink">Coverage Summary</h3>
            <div className="text-sm space-y-2">
              <div className="flex justify-between">
                <span className="text-muted">Coverage:</span>
                <span className="font-medium">{plan.validation?.coverage || 0}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Traceability:</span>
                <span className="font-medium">{plan.validation?.traceability || 0}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Core Passed:</span>
                <span className="font-medium">{plan.validation?.core_passed ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white p-5 rounded-lg border border-border shadow-sm space-y-4">
            <h3 className="font-medium text-ink">Generation Metadata</h3>
            <div className="text-xs font-mono text-muted space-y-2 break-all">
              <p>Model: {plan.model || 'gemini'}</p>
              <p>Prompt Version: {plan.prompt_version || '1.0'}</p>
              <p>Created: {formatDate(plan.created_at)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlanPage;
