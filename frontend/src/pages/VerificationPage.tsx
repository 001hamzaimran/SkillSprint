import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import { ShieldCheck, Info, FileWarning, Search, Save, Scale } from 'lucide-react';
import { cn, truncateId } from '@/lib/utils';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';

import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';

interface VerificationState {
  metrics: {
    effective_count: number;
    excluded_count: number;
    annotated_count: number;
    unannotated_count: number;
    unresolved_conflicts: number;
  };
  dependency_findings: any[];
  conflict_groups: Array<{
    conflict_id: string;
    status: 'unresolved' | 'resolved';
    condition: any;
    requirements: Array<{
      id: string;
      title: string;
      quote?: string;
    }>;
  }>;
  effective_requirements: Array<{
    id: string;
    title: string;
    status: string;
    policy_rule: { key: string; values: string[] };
    prerequisites: string[];
  }>;
}

export function VerificationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const roleIdParam = searchParams.get('role_id') || '';
  const [roleId, setRoleId] = useState(roleIdParam);
  const [roles, setRoles] = useState<Array<{ _id: string; name: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<VerificationState | null>(null);
  
  const { user } = useAuthStore();
  const isReviewer = user?.role === 'reviewer' || user?.role === 'admin';

  const [resolveForm, setResolveForm] = useState<Record<string, { winner_id: string; reason: string }>>({});

  useEffect(() => {
    api.get('roles').json<{ roles: Array<{ _id: string; name: string }> }>()
      .then(res => setRoles(res.roles || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (roleIdParam) {
      setRoleId(roleIdParam);
      fetchVerification(roleIdParam);
    }
  }, [roleIdParam]);

  const fetchVerification = async (rId: string) => {
    setLoading(true);
    try {
      const res = await api.get(`verification?role_id=${rId}`).json<any>();
      if (res && res.state) {
        const state = res.state;
        const eff = state.requirements || [];
        const conflicts = state.conflicts || [];
        setData({
          metrics: {
            effective_count: eff.length,
            excluded_count: state.excluded?.length || 0,
            annotated_count: res.annotated || 0,
            unannotated_count: Math.max(0, eff.length - (res.annotated || 0)),
            unresolved_conflicts: state.unresolved?.length || 0,
          },
          dependency_findings: res.dependencies || [],
          conflict_groups: conflicts.map((g: any) => ({
            conflict_id: g._id,
            status: g.resolution ? 'resolved' : 'unresolved',
            condition: g.condition || g.key,
            requirements: (g.requirements || []).map((r: any) => ({
              id: r.requirement_id || r._id,
              title: r.title,
              quote: r.quote || r.text || r.excerpt,
            })),
          })),
          effective_requirements: eff.map((r: any) => ({
            id: r.requirement_id || r._id,
            title: r.title,
            status: r.status || 'approved',
            policy_rule: r.policy_rule ? { key: r.policy_rule.key, values: [r.policy_rule.value] } : null,
            prerequisites: r.prerequisites || [],
          })),
        });
      } else {
        setData(res);
      }
    } catch {
      toast.error('Failed to load verification state');
    } finally {
      setLoading(false);
    }
  };

  const handleInspect = () => {
    if (!roleId) return;
    setSearchParams({ role_id: roleId });
  };

  const handleResolve = async (conflictId: string) => {
    const form = resolveForm[conflictId];
    if (!form?.winner_id || !form?.reason) {
      toast.error('Please select a winner and provide a reason');
      return;
    }
    
    try {
      await api.post(`verification/${roleId}/resolve`, {
        json: {
          conflict_id: conflictId,
          winner_id: form.winner_id,
          reason: form.reason
        }
      });
      toast.success('Conflict resolved successfully');
      fetchVerification(roleId);
    } catch {
      toast.error('Failed to resolve conflict');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        eyebrow="RULES BEFORE GENERATION" 
        title="Verification center"
      >
        <div className="flex items-center gap-2">
          <div className="w-[200px]">
            <Select value={roleId} onChange={e => setRoleId(e.target.value)}>
              <option value="">Select role...</option>
              {roles.map(r => (
                <option key={r._id} value={r._id}>{r.name}</option>
              ))}
            </Select>
          </div>
          <Button onClick={handleInspect} variant="secondary">
            <Search className="w-4 h-4 mr-2" />
            Inspect role
          </Button>
        </div>
      </PageHeader>

      {!data && !loading && (
        <EmptyState
          icon={<ShieldCheck className="w-10 h-10 text-muted" />}
          title="No role selected"
          description="Select a role and click Inspect to view verification state."
        />
      )}

      {loading && (
        <div className="flex justify-center p-12">
          <Spinner size="lg" />
        </div>
      )}

      {data && !loading && (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              label="Effective requirements"
              value={data.metrics.effective_count.toString()}
              subtext={`${data.metrics.excluded_count} excluded by role`}
            />
            <StatCard
              label="Annotated rules"
              value={data.metrics.annotated_count.toString()}
              subtext={`${data.metrics.unannotated_count} unannotated`}
            />
            <StatCard
              label="Unresolved conflicts"
              value={data.metrics.unresolved_conflicts.toString()}
              subtext="Requires reviewer attention"
            />
          </div>

          {data.dependency_findings && data.dependency_findings.length > 0 && (
            <Card className="border-amber-200 bg-amber-50/50">
              <CardHeader>
                <CardTitle className="text-amber-900 flex items-center gap-2">
                  <FileWarning className="w-5 h-5 text-amber-600" />
                  Dependency findings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc pl-5 space-y-1 text-sm text-amber-800">
                  {data.dependency_findings.map((finding, idx) => (
                    <li key={idx}>{finding}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {data.conflict_groups.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Scale className="w-5 h-5" />
                Conflict resolution
              </h3>
              {data.conflict_groups.map(group => (
                <Card key={group.conflict_id} className={cn(
                  "border-l-4",
                  group.status === 'resolved' ? "border-l-green-500" : "border-l-amber-500"
                )}>
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-base font-medium font-mono text-sm">
                          {group.conflict_id}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Condition: {JSON.stringify(group.condition)}
                        </CardDescription>
                      </div>
                      <Badge variant={group.status === 'resolved' ? 'default' : 'destructive'}>
                        {group.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {group.requirements.map(req => (
                        <div key={req.id} className="p-3 bg-muted/20 rounded-md text-sm border">
                          <div className="font-medium mb-1 truncate" title={req.title}>{req.title}</div>
                          <div className="text-muted-foreground italic line-clamp-3">
                            "{req.quote || 'No quote provided'}"
                          </div>
                        </div>
                      ))}
                    </div>

                    {isReviewer && group.status === 'unresolved' && (
                      <div className="bg-paper p-4 rounded-md border mt-4 space-y-4">
                        <h4 className="text-sm font-medium">Resolve conflict</h4>
                        <div className="space-y-3">
                          <div>
                            <label className="text-xs font-medium text-muted-foreground mb-1 block">Winner requirement</label>
                            <Select 
                              value={resolveForm[group.conflict_id]?.winner_id || ''}
                              onChange={(e) => setResolveForm(prev => ({
                                ...prev,
                                [group.conflict_id]: { ...prev[group.conflict_id], winner_id: e.target.value }
                              }))}
                            >
                              <option value="">Select winning requirement...</option>
                              {group.requirements.map(req => (
                                <option key={req.id} value={req.id}>{req.title}</option>
                              ))}
                            </Select>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-muted-foreground mb-1 block">Resolution reason</label>
                            <Textarea 
                              placeholder="Explain why this requirement wins..."
                              value={resolveForm[group.conflict_id]?.reason || ''}
                              onChange={(e) => setResolveForm(prev => ({
                                ...prev,
                                [group.conflict_id]: { ...prev[group.conflict_id], reason: e.target.value }
                              }))}
                              className="h-20 text-sm resize-none"
                            />
                          </div>
                          <Button 
                            size="sm" 
                            onClick={() => handleResolve(group.conflict_id)}
                            disabled={!resolveForm[group.conflict_id]?.winner_id || !resolveForm[group.conflict_id]?.reason}
                          >
                            <Save className="w-4 h-4 mr-2" />
                            Resolve conflict
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Effective Requirements</h3>
            <div className="border rounded-md overflow-hidden bg-white">
              <table className="w-full text-sm">
                <thead className="bg-muted/10">
                  <tr className="border-b">
                    <th className="text-left font-medium p-3 text-muted-foreground w-24">ID</th>
                    <th className="text-left font-medium p-3 text-muted-foreground">Title</th>
                    <th className="text-left font-medium p-3 text-muted-foreground w-32">Status</th>
                    <th className="text-left font-medium p-3 text-muted-foreground">Policy Rule</th>
                    <th className="text-left font-medium p-3 text-muted-foreground">Prerequisites</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.effective_requirements.map(req => (
                    <tr key={req.id} className="hover:bg-muted/5">
                      <td className="p-3 font-mono text-xs">{truncateId(req.id)}</td>
                      <td className="p-3 font-medium">{req.title}</td>
                      <td className="p-3">
                        <StatusBadge status={req.status as any} />
                      </td>
                      <td className="p-3 text-xs">
                        {req.policy_rule ? (
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold text-ink/70">{req.policy_rule.key}</span>
                            <span className="text-muted-foreground">{req.policy_rule.values?.join(', ')}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground italic">None</span>
                        )}
                      </td>
                      <td className="p-3">
                        {req.prerequisites?.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {req.prerequisites.map(pr => (
                              <Badge key={pr} variant="default" className="text-xs font-mono">
                                {truncateId(pr)}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-xs italic">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {data.effective_requirements.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-muted-foreground">
                        No effective requirements for this role.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VerificationPage;

