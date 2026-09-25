import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router';
import { ArrowLeft, Scale } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePlanStore } from '@/stores/planStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { toast } from 'sonner';

export default function ComparePage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const otherId = searchParams.get('other') || '';

  const { currentPlan, comparison, alternatives, fetchCompare, isLoading } = usePlanStore();
  const [selectedOtherId, setSelectedOtherId] = useState<string>(otherId);

  useEffect(() => {
    if (id) {
      fetchCompare(id, otherId).catch(() => {
        toast.error('Failed to fetch comparison');
      });
    }
  }, [id, otherId, fetchCompare]);

  useEffect(() => {
    if (otherId) {
      setSelectedOtherId(otherId);
    } else if (alternatives.length > 0) {
      setSelectedOtherId(alternatives[0]._id);
    }
  }, [otherId, alternatives]);

  const handleCompare = () => {
    if (selectedOtherId) {
      setSearchParams({ other: selectedOtherId });
    }
  };

  if (isLoading && !currentPlan) {
    return <div className="p-8 flex justify-center"><Spinner size="lg" /></div>;
  }

  if (!currentPlan) {
    return <EmptyState title="Plan not found" description="Could not load the requested plan." />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="flex items-center gap-2 text-sm text-muted mb-4">
        <Link to={`/plans/${id}`} className="hover:text-ink flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Plan
        </Link>
      </div>

      <PageHeader 
        eyebrow="SEE THE DIFFERENCE" 
        title="Compare plan versions" 
      />

      <Card className="bg-paper border-border">
        <CardContent className="p-6 flex items-end gap-4">
          <div className="flex-1 max-w-md space-y-2">
            <label className="text-sm font-medium text-ink">Select alternative version</label>
            <Select 
              value={selectedOtherId} 
              onChange={(e) => setSelectedOtherId(e.target.value)}
              className="bg-white"
            >
              <option value="" disabled>Select a plan version</option>
              {alternatives.map(plan => (
                <option key={plan._id} value={plan._id}>
                  {plan.content?.title || plan._id} ({plan.status})
                </option>
              ))}
            </Select>
          </div>
          <Button 
            onClick={handleCompare} 
            disabled={!selectedOtherId || isLoading}
            className="bg-green text-white hover:bg-green/90"
          >
            {isLoading ? <Spinner size="sm" className="mr-2" /> : <Scale className="w-4 h-4 mr-2" />}
            Compare
          </Button>
        </CardContent>
      </Card>

      {!otherId ? (
        <EmptyState 
          icon={<Scale className="w-10 h-10 text-muted" />}
          title="Select a version to compare" 
          description="Choose an alternative plan version for this employee to see what changed." 
        />
      ) : !comparison ? (
        isLoading ? (
          <div className="p-12 flex justify-center"><Spinner size="lg" /></div>
        ) : (
          <EmptyState title="No comparison data" description="Could not load comparison." />
        )
      ) : (
        <div className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard 
              label="Consistency Score" 
              value={comparison.consistency_score !== null ? `${(comparison.consistency_score * 100).toFixed(0)}%` : 'N/A'} 
              subtext={comparison.method}
            />
            <StatCard 
              label="Method Used" 
              value={comparison.method || "Set overlap"} 
            />
            <StatCard 
              label="Categories Evaluated" 
              value={comparison.categories?.length || 0} 
              subtext={comparison.limitation}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Categories Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border border-border rounded-md overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-paper border-b border-border text-muted">
                    <tr>
                      <th className="px-4 py-3 font-medium">Category Name</th>
                      <th className="px-4 py-3 font-medium">Score</th>
                      <th className="px-4 py-3 font-medium">Intersection</th>
                      <th className="px-4 py-3 font-medium">Union</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border bg-white">
                    {comparison.categories?.map((cat, i) => (
                      <tr key={i} className="hover:bg-paper/50">
                        <td className="px-4 py-3 font-medium text-ink">{cat.category}</td>
                        <td className="px-4 py-3">{cat.score !== null ? `${(cat.score * 100).toFixed(0)}%` : '—'}</td>
                        <td className="px-4 py-3">{cat.intersection}</td>
                        <td className="px-4 py-3">{cat.union}</td>
                      </tr>
                    ))}
                    {(!comparison.categories || comparison.categories.length === 0) && (
                      <tr><td colSpan={4} className="px-4 py-8 text-center text-muted">No category data available</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-ink">
              Module Comparison
            </h3>
            
            {comparison.rows?.map((mod, i) => (
              <Card key={i} className={cn("overflow-hidden border", mod.status === 'Changed' ? 'border-amber/50' : mod.status === 'Added' ? 'border-green/50' : mod.status === 'Removed' ? 'border-red-200' : 'border-border')}>
                <div className="bg-paper px-4 py-3 border-b border-border flex justify-between items-center">
                  <span className="font-medium text-ink truncate max-w-[60%]">
                    {mod.left?.module_title || mod.right?.module_title || mod.requirement_id}
                  </span>
                  <StatusBadge 
                    status={mod.status === 'Added' ? 'completed' : mod.status === 'Removed' ? 'failed' : mod.status === 'Changed' ? 'warning' : 'default'} 
                  />
                </div>
                <div className="grid grid-cols-2 divide-x divide-border">
                  <div className="p-4 bg-white/50 space-y-3">
                    <div className="text-xs font-semibold text-muted uppercase tracking-wider">Current Version (Left)</div>
                    {mod.left ? (
                      <>
                        <div>
                          <p className="text-sm font-medium text-ink">{mod.left.module_title}</p>
                          <p className="text-xs text-muted">{mod.left.estimated_minutes} mins · Stage: {mod.left.stage}</p>
                        </div>
                        {mod.left.learning_objective && (
                          <div>
                            <p className="text-xs font-medium text-muted">Objective</p>
                            <p className="text-sm text-ink">{mod.left.learning_objective}</p>
                          </div>
                        )}
                        {mod.left.quiz && (
                          <div>
                            <p className="text-xs font-medium text-muted">Quiz Question</p>
                            <p className="text-xs text-ink">{mod.left.quiz.question}</p>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-muted italic">Not present in this version</p>
                    )}
                  </div>
                  <div className="p-4 bg-white/50 space-y-3">
                    <div className="text-xs font-semibold text-muted uppercase tracking-wider">Comparison Version (Right)</div>
                    {mod.right ? (
                      <>
                        <div>
                          <p className="text-sm font-medium text-ink">{mod.right.module_title}</p>
                          <p className="text-xs text-muted">{mod.right.estimated_minutes} mins · Stage: {mod.right.stage}</p>
                        </div>
                        {mod.right.learning_objective && (
                          <div>
                            <p className="text-xs font-medium text-muted">Objective</p>
                            <p className="text-sm text-ink">{mod.right.learning_objective}</p>
                          </div>
                        )}
                        {mod.right.quiz && (
                          <div>
                            <p className="text-xs font-medium text-muted">Quiz Question</p>
                            <p className="text-xs text-ink">{mod.right.quiz.question}</p>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-muted italic">Not present in this version</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
