import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { ArrowLeft, Users, FileStack, AlertCircle, ArrowRight, BookOpen, Clock } from 'lucide-react';
import api from '@/lib/api';
import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';

export default function ImpactPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (id) {
      setLoading(true);
      api.get(`documents/${id}/impact`).json<any>()
        .then((res: any) => {
          setData(res);
          setLoading(false);
        })
        .catch(() => {
          setError(true);
          setLoading(false);
          toast.error('Failed to load impact preview');
        });
    }
  }, [id]);

  if (loading) {
    return <div className="p-12 flex justify-center"><Spinner size="lg" /></div>;
  }

  if (error || !data) {
    return <EmptyState title="Impact analysis unavailable" description="Could not load the impact analysis for this document." />;
  }

  const { document: doc, previous = [], affected = [], old_requirements = [], new_requirements = [] } = data;

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="flex items-center gap-2 text-sm text-muted mb-4">
        <Link to={`/documents/${id}`} className="hover:text-ink flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Document
        </Link>
      </div>

      <PageHeader 
        eyebrow="BEFORE THE POLICY CHANGES" 
        title="Policy change preview" 
        subtitle={doc ? `${doc.title} (${doc.document_id} v${doc.version})` : undefined}
      />

      <div className="bg-lime/20 border border-lime/50 rounded-md p-4 flex gap-3 text-ink items-start">
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-green" />
        <div>
          <h4 className="font-semibold text-sm">Non-destructive preview</h4>
          <p className="text-sm mt-1 text-muted">Existing published plans remain intact until explicitly updated. This analysis shows the potential impact if updates are applied.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard 
          label="Affected Learners" 
          value={affected.length} 
          subtext="Employees with active plans"
        />
        <StatCard 
          label="Active Versions Replaced" 
          value={previous.length} 
          subtext="Prior versions superseded"
        />
        <StatCard 
          label="New Requirements" 
          value={new_requirements.length} 
          subtext="Defined in this document"
        />
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-green" /> Affected Learners
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-paper border-y border-border text-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Employee</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    <th className="px-4 py-3 font-medium">Active Plan Title</th>
                    <th className="px-4 py-3 font-medium">Affected Modules</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-white">
                  {affected.map((item: any, i: number) => (
                    <tr key={i} className="hover:bg-paper/50">
                      <td className="px-4 py-4">
                        <div className="font-medium text-ink">{item.employee?.name}</div>
                      </td>
                      <td className="px-4 py-4 text-muted">{item.employee?.role_name}</td>
                      <td className="px-4 py-4">{item.plan?.content?.title || 'Active Plan'}</td>
                      <td className="px-4 py-4">
                        <div className="flex gap-2 items-center">
                          <span className="font-medium">{item.items?.length || 0} modules</span>
                          <span className="text-xs text-muted">({item.checklists || 0} checklists, {item.quizzes || 0} quizzes)</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Link to={`/plans/${item.plan?._id}/update`}>
                          <Button variant="secondary" size="sm" className="h-8">
                            Inspect update <ArrowRight className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {affected.length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-muted">No learners currently affected.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-amber" /> Requirements Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-semibold text-sm text-muted uppercase">Old Requirements ({old_requirements.length})</h4>
                <div className="bg-paper p-4 rounded-md border border-border min-h-[200px] text-sm space-y-3 text-ink">
                  {old_requirements.map((r: any) => (
                    <div key={r._id} className="border-b border-border/50 pb-2">
                      <p className="font-medium text-xs">{r.title}</p>
                      <p className="text-xs text-muted mt-1">{r.text}</p>
                    </div>
                  ))}
                  {old_requirements.length === 0 && <p className="text-muted italic">No old requirements found.</p>}
                </div>
              </div>
              <div className="space-y-4">
                <h4 className="font-semibold text-sm text-green uppercase">New Requirements ({new_requirements.length})</h4>
                <div className="bg-lime/10 p-4 rounded-md border border-lime/50 min-h-[200px] text-sm space-y-3 text-ink">
                  {new_requirements.map((r: any) => (
                    <div key={r._id} className="border-b border-lime/30 pb-2">
                      <p className="font-medium text-xs">{r.title}</p>
                      <p className="text-xs text-muted mt-1">{r.text}</p>
                    </div>
                  ))}
                  {new_requirements.length === 0 && <p className="text-muted italic">No new requirements found.</p>}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
