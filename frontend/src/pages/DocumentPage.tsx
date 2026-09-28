import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { useAuthStore } from '@/stores/authStore';
import { useDocumentStore } from '@/stores/documentStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Spinner } from '@/components/shared/Spinner';
import * as Collapsible from '@radix-ui/react-collapsible';
import { ArrowLeft, Download, AlertTriangle, Sparkles, CheckCircle2, ChevronDown, Check, X } from 'lucide-react';
import { formatDate, formatDateTime } from '@/lib/utils';
import { toast } from 'sonner';
import api from '@/lib/api';
import { STAGES } from '@/types';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { useHashTarget } from '@/lib/useHashTarget';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const { currentDocument: doc, sections, requirements, jobs, roles, fetchDocument, isLoading } = useDocumentStore();
  const [isExtracting, setIsExtracting] = useState(false);
  const [isActivating, setIsActivating] = useState(false);
  const sourceTarget = useHashTarget(!isLoading && doc?._id === id);

  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';
  const isReviewer = user?.role === 'admin' || user?.role === 'reviewer';

  useEffect(() => {
    if (id) {
      fetchDocument(id).catch(() => toast.error('Failed to load document'));
    }
  }, [id, fetchDocument]);

  const handleExtract = async () => {
    if (!id) return;
    try {
      setIsExtracting(true);
      await api.post(`documents/${id}/extract`);
      toast.success('Extraction job started');
      fetchDocument(id);
    } catch {
      toast.error('Failed to start extraction');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleActivate = async () => {
    if (!id) return;
    try {
      setIsActivating(true);
      await api.post(`documents/${id}/activate`);
      toast.success('Document activated');
      fetchDocument(id);
    } catch (err: any) {
      toast.error(err.message || 'Failed to activate document');
    } finally {
      setIsActivating(false);
    }
  };

  const handleReview = async (reqId: string, decision: string) => {
    try {
      const req = requirements.find(r => r._id === reqId);
      if (!req) return;
      await api.post(`requirements/${reqId}/review`, {
        json: {
          title: req.title,
          text: req.text,
          mandatory: req.mandatory ? 'true' : 'false',
          due_stage: req.due_stage || 'Day 1',
          role_id: req.role_ids[0] || '',
          priority: (req as any).priority || 'Medium',
          classification: (req as any).classification || 'Must Know',
          decision,
        },
      });
      toast.success(`Requirement ${decision}`);
      if (id) fetchDocument(id);
    } catch {
      toast.error('Failed to review requirement');
    }
  };

  if (isLoading || !doc) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      <div>
        <Link to="/documents" className="inline-flex items-center text-sm font-medium text-muted hover:text-ink mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" /> Knowledge library
        </Link>
        <PageHeader 
          eyebrow={`${doc.document_id} · v${doc.version}`}
          title={doc.title}
          subtitle={`Category: ${doc.category} · Effective: ${formatDate(doc.effective_date)}`}
        />
      </div>

      <div className="bg-white border border-border rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <StatusBadge status={doc.status} />
            <span className="text-sm font-semibold text-ink uppercase tracking-wider">{doc.category}</span>
          </div>
          <div className="text-sm text-muted space-x-4">
            <span>Effective: {formatDate(doc.effective_date)}</span>
            <span>Added: {formatDate(doc.created_at)}</span>
          </div>
        </div>

        <div className="flex flex-col gap-3 min-w-[200px]">
          <Button variant="secondary" asChild className="w-full justify-start">
            <a href={`/documents/${doc._id}/download`} target="_blank" rel="noreferrer">
              <Download className="w-4 h-4 mr-2" /> Download original
            </a>
          </Button>
          
          {doc.status === 'active' && (
            <Button variant="secondary" asChild className="w-full justify-start">
              <Link to={`/documents/${doc._id}/impact`}>Preview policy impact</Link>
            </Button>
          )}

          {isReviewer && doc.status === 'draft' && (
            <Button 
              onClick={handleActivate} 
              disabled={isActivating}
              className="w-full justify-start bg-green text-white hover:bg-green/90"
            >
              <CheckCircle2 className="w-4 h-4 mr-2" /> 
              {isActivating ? 'Activating...' : 'Approve source version'}
            </Button>
          )}

          {isEditor && (
            <Button 
              onClick={handleExtract} 
              disabled={isExtracting}
              className="w-full justify-start bg-ink text-white hover:bg-ink/90"
            >
              <Sparkles className="w-4 h-4 mr-2" /> 
              {isExtracting ? 'Extracting...' : 'Extract with AI'}
            </Button>
          )}
        </div>
      </div>

      {doc.suspicious && (
        <div className="bg-amber/10 border border-amber/30 rounded-xl p-5 flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-amber shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-amber-900 mb-1">Suspicious content detected</h3>
            <p className="text-amber-800/80 text-sm">Our AI checks flagged some potential issues in this document. Please review the highlighted sections carefully before approving requirements.</p>
          </div>
        </div>
      )}

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Requirements */}
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold text-ink">Requirement candidates</h2>
            <span className="text-sm text-muted">{requirements?.length || 0} found</span>
          </div>

          {!requirements || requirements.length === 0 ? (
            <div className="bg-paper border border-border border-dashed rounded-xl p-8 text-center">
              <p className="text-muted text-sm">No requirements extracted yet. Run "Extract with AI" to find them.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {requirements.map((req) => (
                <Collapsible.Root key={req._id} className="bg-white border border-border rounded-lg overflow-hidden shadow-sm">
                  <Collapsible.Trigger className="w-full flex items-center justify-between p-4 hover:bg-slate-50">
                    <div className="flex items-center gap-3 text-left">
                      <StatusBadge status={req.status || 'draft'} />
                      <span className="font-medium text-ink line-clamp-1">{req.title || 'Untitled Requirement'}</span>
                    </div>
                    <ChevronDown className="w-4 h-4 text-muted" />
                  </Collapsible.Trigger>
                  <Collapsible.Content className="p-4 border-t border-border bg-slate-50/50">
                    <div className="space-y-4">
                      <p className="text-sm text-ink">{req.text}</p>
                      {isReviewer && <Link className="text-green underline text-sm" to={`/requirements/${req._id}/rules`}>Edit rules and prerequisites</Link>}
                      {isReviewer && <details><summary className="cursor-pointer text-green">Edit requirement review</summary><form className="space-y-3 pt-3" onSubmit={async event => {
                        event.preventDefault();
                        const json = Object.fromEntries(new FormData(event.currentTarget));
                        try { await api.post(`requirements/${req._id}/review`, { json }); await fetchDocument(id!); toast.success('Requirement review saved.'); }
                        catch (error: any) { const body = await error.response?.json(); toast.error(body?.detail || 'Could not save review.'); }
                      }}>
                        <label className="block">Title<Input name="title" defaultValue={req.title} required /></label>
                        <label className="block">Exact source passage<Textarea name="text" defaultValue={req.text} required /></label>
                        <label className="block">Obligation<Select name="mandatory" defaultValue={String(req.mandatory)}><option value="true">Mandatory</option><option value="false">Optional</option></Select></label>
                        <label className="block">Due stage<Select name="due_stage" defaultValue={req.due_stage}>{STAGES.map(stage => <option key={stage}>{stage}</option>)}</Select></label>
                        <label className="block">Role<Select name="role_id" defaultValue={req.role_ids[0] || ''}><option value="">All roles</option>{roles.map(role => <option key={role._id} value={role._id}>{role.name}</option>)}</Select></label>
                        <label className="block">Priority<Select name="priority" defaultValue={(req as any).priority || 'Medium'}>{['High', 'Medium', 'Low'].map(value => <option key={value}>{value}</option>)}</Select></label>
                        <label className="block">Requirement type<Select name="classification" defaultValue={(req as any).classification || 'Must Know'}>{['Must Know', 'Must Complete', 'Must Demonstrate', 'Must Acknowledge', 'Recommended', 'Optional', 'Not Applicable'].map(value => <option key={value}>{value}</option>)}</Select></label>
                        <label className="block">Decision<Select name="decision" defaultValue={req.status}>{['draft', 'approved', 'rejected'].map(value => <option key={value}>{value}</option>)}</Select></label>
                        <Button>Save review</Button>
                      </form></details>}
                      
                      {isReviewer && req.status !== 'approved' && (
                        <div className="pt-4 border-t border-border mt-4 flex gap-2">
                          <Button size="sm" onClick={() => handleReview(req._id, 'approved')} className="bg-green text-white flex-1">
                            <Check className="w-4 h-4 mr-1"/> Approve
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => handleReview(req._id, 'rejected')} className="text-red-600 hover:text-red-700 flex-1">
                            <X className="w-4 h-4 mr-1"/> Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  </Collapsible.Content>
                </Collapsible.Root>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Source Evidence */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-ink mb-2">Source evidence</h2>
          
          {!sections || sections.length === 0 ? (
            <div className="bg-paper border border-border border-dashed rounded-xl p-8 text-center">
              <p className="text-muted text-sm">No source sections available.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sections.map((section, idx) => (
                <Collapsible.Root key={section._id || idx} id={section.section_id} defaultOpen={sourceTarget === section.section_id} className="bg-white border border-border rounded-lg overflow-hidden scroll-m-6">
                  <Collapsible.Trigger className="w-full flex items-center justify-between p-3 hover:bg-slate-50 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-ink">{section.heading || `Section ${idx + 1}`}</span>
                      {section.suspicious && <AlertTriangle className="w-4 h-4 text-amber" />}
                    </div>
                    <ChevronDown className="w-4 h-4 text-muted" />
                  </Collapsible.Trigger>
                  <Collapsible.Content className="p-4 border-t border-border bg-slate-50 font-mono text-xs overflow-x-auto whitespace-pre-wrap text-ink">
                    {section.text}
                  </Collapsible.Content>
                </Collapsible.Root>
              ))}
            </div>
          )}
          
          {jobs && jobs.length > 0 && (
            <div className="mt-8 pt-6 border-t border-border">
              <h3 className="text-sm font-semibold uppercase text-muted mb-4">Recent Extraction Jobs</h3>
              <div className="space-y-2">
                {jobs.map((job) => (
                  <Link key={job._id} to={`/jobs/${job._id}`} className="flex items-center justify-between p-3 bg-white border border-border rounded-lg hover:border-green transition-colors">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-muted" />
                      <span className="text-sm font-medium">{formatDateTime(job.created_at)}</span>
                    </div>
                    <StatusBadge status={job.status} />
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
