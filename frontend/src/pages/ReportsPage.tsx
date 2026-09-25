import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router';
import { Download, Search, SearchX, FileSpreadsheet, User, BarChart } from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

import { PageHeader } from '@/components/shared/PageHeader';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [q, setQ] = useState(searchParams.get('q') || '');
  const [roleId, setRoleId] = useState(searchParams.get('role_id') || 'all');
  const [status, setStatus] = useState(searchParams.get('status') || 'all');
  
  const [reports, setReports] = useState<any[]>([]);
  const [roles, setRoles] = useState<Array<{ _id: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (roleId && roleId !== 'all') params.set('role_id', roleId);
      if (status && status !== 'all') params.set('status', status);
      
      const data = await api.get(`reports?${params.toString()}`).json<{ rows: any[]; roles: Array<{ _id: string; name: string }> }>();
      setRoles(data.roles);
      setReports(data.rows.map(row => ({
        employee_name: row.employee.name,
        employee_role: row.employee.role_name,
        plan: { ...row.plan, title: row.plan.content.title, is_assigned: row.assigned, sources_current: row.current },
        metrics: { coverage_percent: row.plan.validation.coverage, traceability_percent: row.plan.validation.traceability },
        learning: {
          progress_percent: row.progress.percent,
          mandatory_completed: row.progress.mandatory_completed,
          mandatory_total: row.progress.mandatory_total,
          overdue_count: row.progress.overdue,
          weak_competencies: row.progress.weak.length,
        },
      })));
    } catch {
      toast.error('Failed to load reports');
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
    // eslint-disable-next-line
  }, [searchParams]);

  const handleApplyFilters = () => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (roleId !== 'all') params.set('role_id', roleId);
    if (status !== 'all') params.set('status', status);
    setSearchParams(params);
  };

  const exportUrl = `/reports.csv?${searchParams.toString()}`;

  return (
    <div className="space-y-6">
      <PageHeader 
        eyebrow="MEASURE WHAT MATTERS" 
        title="Learning and validation reports"
      >
        <Button asChild variant="secondary">
          <a href={exportUrl} download>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </a>
        </Button>
      </PageHeader>

      <div className="flex flex-col sm:flex-row gap-3 bg-white p-4 rounded-lg border">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <Input 
            placeholder="Search employee or plan..." 
            className="pl-9"
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleApplyFilters()}
          />
        </div>
        <div className="w-[180px]">
          <Select value={roleId} onChange={e => setRoleId(e.target.value)}>
            <option value="all">All Roles</option>
            {roles.map(role => <option key={role._id} value={role._id}>{role.name}</option>)}
          </Select>
        </div>
        <div className="w-[180px]">
          <Select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="all">All Statuses</option>
            {['Published', 'Review required', 'Needs correction', 'Rejected', 'Stale sources'].map(value => <option key={value} value={value}>{value}</option>)}
          </Select>
        </div>
        <Button onClick={handleApplyFilters}>Apply filters</Button>
      </div>

      {loading ? (
        <div className="flex justify-center p-12"><Spinner size="lg" /></div>
      ) : reports.length === 0 ? (
        <EmptyState
          icon={<SearchX className="w-10 h-10 text-muted" />}
          title="No reports found"
          description="Adjust your filters or search query to find more results."
        />
      ) : (
        <div className="border rounded-md overflow-hidden bg-white overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/10">
              <tr className="border-b">
                <th className="text-left font-medium p-4 text-muted-foreground">Employee</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Plan</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Validation</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Progress</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Metrics</th>
                <th className="text-right font-medium p-4 text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {reports.map((r, i) => (
                <tr key={i} className="hover:bg-muted/5 group">
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-xs">
                        {r.employee_name?.charAt(0) || 'U'}
                      </div>
                      <div>
                        <div className="font-medium text-ink">{r.employee_name}</div>
                        <div className="text-xs text-muted-foreground">{r.employee_role}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <Link to={`/plans/${r.plan?._id}`} className="font-medium text-primary hover:underline block mb-1">
                      {r.plan?.title || 'Unnamed Plan'}
                    </Link>
                    <div className="flex gap-2 mt-1 flex-wrap">
                      <StatusBadge status={r.plan?.status || 'draft'} />
                      {r.plan?.is_assigned && <Badge variant="default" className="text-[10px]">Assigned</Badge>}
                      {r.plan?.sources_current && <Badge className="bg-green-100 text-green-800 hover:bg-green-100 text-[10px]">Sources current</Badge>}
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Coverage</span>
                        <span className="font-medium">{r.metrics?.coverage_percent ?? 0}%</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Traceability</span>
                        <span className="font-medium">{r.metrics?.traceability_percent ?? 0}%</span>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <Link to={`/learning/${r.plan?._id}`} className="block hover:opacity-80">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-medium text-primary">Learning progress</span>
                        <span className="font-bold">{r.learning?.progress_percent ?? 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted/20 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-full" 
                          style={{ width: `${r.learning?.progress_percent ?? 0}%` }} 
                        />
                      </div>
                    </Link>
                  </td>
                  <td className="p-4">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-muted-foreground block">Mandatory</span>
                        <span className="font-medium">{r.learning?.mandatory_completed || 0} / {r.learning?.mandatory_total || 0}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">Overdue</span>
                        <span className={cn("font-medium", (r.learning?.overdue_count || 0) > 0 ? "text-destructive" : "")}>
                          {r.learning?.overdue_count || 0}
                        </span>
                      </div>
                      <div className="col-span-2 mt-1">
                        <span className="text-muted-foreground block">Weak comps.</span>
                        <span className={cn("font-medium", (r.learning?.weak_competencies || 0) > 0 ? "text-amber-600" : "")}>
                          {r.learning?.weak_competencies || 0}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <Button variant="ghost" size="sm" asChild className="h-8">
                      <a href={`/plans/${r.plan?._id}/validation.csv`} download>
                        <FileSpreadsheet className="w-3 h-3 mr-2" />
                        Validation CSV
                      </a>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ReportsPage;
