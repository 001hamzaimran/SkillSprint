import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/shared/PageHeader';
import { toast } from 'sonner';

type RecordData = Record<string, any>;
const panel = 'bg-white rounded-xl border border-border p-5 space-y-4';

type WorkspaceMode = 'search' | 'insights' | 'review-queue' | 'settings' | 'manage' | 'compare';

export default function WorkspacePage({ mode }: { mode: WorkspaceMode }) {
  // Each screen has a different response shape. Reset before rendering a new mode,
  // not in an effect after it has already tried to render the previous data.
  return <WorkspaceScreen key={mode} mode={mode} />;
}

function WorkspaceScreen({ mode }: { mode: WorkspaceMode }) {
  const active = useRef(false);
  const pendingLoad = useRef<AbortController | null>(null);
  const [data, setData] = useState<RecordData | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [department, setDepartment] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [comparison, setComparison] = useState<RecordData | null>(null);
  async function load() {
    if (!active.current) return;
    pendingLoad.current?.abort();
    const controller = new AbortController();
    pendingLoad.current = controller;
    setError('');
    setData(null);
    try {
      const endpoint = mode === 'settings' ? 'settings/stages' : mode === 'manage' ? 'employees' : mode === 'compare' ? 'plans' : mode;
      const params = mode === 'search' ? { q: query, department, status } : {};
      const result = await api.get(endpoint, { searchParams: params, signal: controller.signal }).json<RecordData>();
      if (active.current && pendingLoad.current === controller && !controller.signal.aborted) {
        setData(result);
      }
    } catch {
      if (active.current && pendingLoad.current === controller && !controller.signal.aborted) {
        setError('Unable to load this workspace. Please retry.');
      }
    }
  }
  useEffect(() => {
    active.current = true;
    void load();
    return () => {
      active.current = false;
      pendingLoad.current?.abort();
    };
  }, []);
  async function save(path: string, json: RecordData) {
    setBusy(true);
    try { await api.put(path, { json }); toast.success('Changes saved'); await load(); }
    catch (error: any) {
      const body = await error.response?.json().catch(() => null);
      toast.error(typeof body?.detail === 'string' ? body.detail : 'Unable to save. Check all fields.');
    } finally { setBusy(false); }
  }
  const title = { search: 'Search the workspace', insights: 'Progress and recommendations', 'review-queue': 'Review queue', settings: 'Onboarding schedule', manage: 'Manage people and roles', compare: 'Compare learning plans' }[mode];
  return <div className="space-y-6 max-w-6xl mx-auto">
    <PageHeader eyebrow="SKILLSPRINT WORKSPACE" title={title} />
    {error && <div role="alert" className={panel}>{error} <Button onClick={load}>Retry</Button></div>}
    {!data && !error && <p role="status">Loading…</p>}
    {mode === 'search' && <form className={panel + ' flex flex-wrap gap-3'} onSubmit={event => { event.preventDefault(); void load(); }}>
      <Input aria-label="Search terms" placeholder="Employee, role, policy or module…" value={query} onChange={event => setQuery(event.target.value)} />
      <Input aria-label="Department filter" placeholder="Department" value={department} onChange={event => setDepartment(event.target.value)} />
      <Input aria-label="Status filter" placeholder="Status (for example Published or active)" value={status} onChange={event => setStatus(event.target.value)} />
      <Button type="submit">Search</Button>
    </form>}
    {data && mode === 'search' && <div className="grid md:grid-cols-2 gap-5">{['employees', 'roles', 'documents', 'modules'].map(kind => <section className={panel} key={kind}>
      <h2 className="font-semibold capitalize">{kind} ({data[kind].length})</h2>
      {data[kind].map((record: RecordData, index: number) => <p key={record._id || index}><Link className="text-green underline" to={kind === 'documents' ? `/documents/${record._id}` : kind === 'modules' ? `/plans/${record.plan_id}` : kind === 'roles' ? '/roles' : '/employees'}>{record.name || record.title || record.item.module_title}</Link></p>)}
    </section>)}</div>}
    {data && mode === 'settings' && <form className={panel} onSubmit={event => { event.preventDefault(); void save('settings/stages', { days: data.days }); }}>
      <p>Days after joining. New plans keep a snapshot of this schedule; existing deadlines remain unchanged.</p>
      {Object.entries(data.days).map(([stage, days]) => <label key={stage} className="grid grid-cols-2 gap-3 items-center">{stage}<Input type="number" min={0} max={365} value={Number(days)} onChange={event => setData({ ...data, days: { ...data.days, [stage]: Number(event.target.value) } })} /></label>)}
      <Button disabled={busy}>Save schedule</Button>
    </form>}
    {data && mode === 'insights' && <>
      <div className="grid md:grid-cols-3 gap-4">{data.roles.map((role: RecordData) => <section className={panel} key={role.role_id}><h2 className="font-semibold">{role.name}</h2><p className="text-3xl font-bold">{role.average_progress}%</p><p>{role.completed} of {role.employees} employees completed</p></section>)}</div>
      {data.people.map((person: RecordData) => <section className={panel} key={person.employee._id}><div className="flex justify-between gap-4"><h2 className="font-semibold">{person.employee.name}</h2><span>{person.status} · {person.percent}%</span></div>
        {person.recommendations.map((r: RecordData, i: number) => <p key={i}><strong>{r.competency}:</strong> {r.message}</p>)}
        {person.plan_id && <Link className="text-green underline" to={`/learning/${person.plan_id}`}>Open learning plan</Link>}
      </section>)}
    </>}
    {data && mode === 'review-queue' && <>{data.plans.length === 0 && <p>No plans awaiting review.</p>}{data.plans.map((plan: RecordData) => <section className={panel} key={plan._id}>
      <h2 className="font-semibold">{plan.content.title} · {data.employees[plan.employee_id]?.name}</h2><p>{plan.status} · {plan.validation.findings.length} findings</p>
      <Link className="text-green underline" to={`/plans/${plan._id}`}>Review, edit or regenerate</Link>
      {(plan.validation.warnings || []).map((warning: RecordData, i: number) => <form key={i} className="border-t pt-4 space-y-2" onSubmit={async event => { event.preventDefault(); const reason = new FormData(event.currentTarget).get('reason'); try { await api.post(`plans/${plan._id}/overrides`, { json: { code: warning.code, requirement_id: warning.requirement_id || '', reason } }); toast.success('Recommendation override recorded; original result preserved.'); } catch { toast.error('Could not record the decision.'); } }}>
        <p>{warning.message}</p><Input name="reason" minLength={10} maxLength={3000} required placeholder="Why is this advisory recommendation not applicable?" aria-label="Override reason" /><Button variant="secondary">Record advisory override</Button>
      </form>)}
    </section>)}</>}
    {data && mode === 'manage' && <>
      <h2 className="text-xl font-semibold">Employees</h2>
      {data.employees.map((employee: RecordData) => <details className={panel} key={employee._id}><summary className="cursor-pointer font-semibold">{employee.name} · {employee.role_name}</summary>
        <form className="grid md:grid-cols-2 gap-4" onSubmit={event => { event.preventDefault(); void save(`employees/${employee._id}`, Object.fromEntries(new FormData(event.currentTarget))); }}>
          <label>Name<Input name="name" defaultValue={employee.name} required /></label>
          <label>Joining date<Input type="date" name="joining_date" defaultValue={employee.joining_date} required /></label>
          <label>Role<Select name="role_id" defaultValue={employee.role_id}>{data.roles.map((r: RecordData) => <option value={r._id} key={r._id}>{r.name}</option>)}</Select></label>
          <label>Experience<Select name="experience" defaultValue={employee.experience}>{['Beginner', 'Intermediate', 'Advanced'].map(level => <option key={level}>{level}</option>)}</Select></label>
          <label>Manager<Select name="manager_id" defaultValue={employee.manager_id || ''}><option value="">Not assigned</option>{data.managers.map((r: RecordData) => <option value={r._id} key={r._id}>{r.name}</option>)}</Select></label>
          <label>Employee login<Select name="user_id" defaultValue={employee.user_id || ''}><option value="">Not linked</option>{data.accounts.map((r: RecordData) => <option value={r._id} key={r._id}>{r.name} ({r.email})</option>)}</Select></label>
          <Button disabled={busy}>Save employee</Button>
        </form>
      </details>)}
      <h2 className="text-xl font-semibold">Roles</h2>
      {data.roles.map((role: RecordData) => <details className={panel} key={role._id}><summary className="cursor-pointer font-semibold">{role.name}</summary>
        <form className="space-y-3" onSubmit={event => { event.preventDefault(); void save(`roles/${role._id}`, Object.fromEntries(new FormData(event.currentTarget))); }}>
          <label>Name<Input name="name" defaultValue={role.name} required /></label><label>Department<Input name="department" defaultValue={role.department} required /></label><label>Description<Input name="description" defaultValue={role.description} /></label><Button disabled={busy}>Save role</Button>
        </form>
      </details>)}
    </>}
    {data && mode === 'compare' && <>
      <form className={panel} onSubmit={async event => { event.preventDefault(); try { setComparison(await api.get('compare', { searchParams: { left, right } }).json<RecordData>()); } catch { toast.error('Could not compare these plans.'); } }}>
        <p>Compare roles, departments, employee levels, or policy versions. Consistency is scored only when generation inputs match.</p>
        {[{ label: 'First plan', value: left, set: setLeft }, { label: 'Second plan', value: right, set: setRight }].map(field => <label key={field.label}>{field.label}<Select value={field.value} onChange={event => field.set(event.target.value)} required><option value="">Choose a plan</option>{data.plans.map((p: RecordData) => <option key={p._id} value={p._id}>{data.employees[p.employee_id]?.name} · {p.content.title} · {p.created_at}</option>)}</Select></label>)}
        <Button disabled={!left || !right}>Compare</Button>
      </form>
      {comparison && <section className={panel}><h2 className="font-semibold">Structured comparison</h2><p>{comparison.comparison.comparable ? `Consistency: ${comparison.comparison.consistency_score}%` : 'Different inputs — differences do not imply generation inconsistency.'}</p>{comparison.comparison.categories.map((c: RecordData) => <p key={c.category}>{c.category.replaceAll('_', ' ')}: {c.score ?? 'N/A'}% overlap</p>)}{comparison.comparison.rows.map((r: RecordData) => <p key={r.requirement_id}>{r.requirement_id}: {r.status}</p>)}</section>}
    </>}
  </div>;
}
