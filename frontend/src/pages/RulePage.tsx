import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

export default function RulePage() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  useEffect(() => { api.get(`requirements/${id}`).json().then(setData).catch(() => setError('Unable to load requirement.')); }, [id]);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const json = Object.fromEntries(new FormData(event.currentTarget));
    try { await api.post(`requirements/${id}/rules`, { json }); toast.success('Rules saved; affected plans need revalidation.'); }
    catch (err: any) { const body = await err.response?.json(); toast.error(body?.detail || 'Unable to save rules.'); }
  }
  if (!data) return <p>{error || 'Loading requirement…'}</p>;
  const req = data.requirement;
  return <section className="max-w-3xl space-y-6">
    <Link to={`/documents/${req.document_id}`} className="text-green underline">Back to source document</Link>
    <h1 className="text-2xl font-bold">Rules and prerequisites: {req.title}</h1>
    <blockquote className="bg-lime/20 border-l-4 border-green p-5 whitespace-pre-wrap">{req.text}</blockquote>
    <p>Use exact source excerpts for the value, condition, exception and answer fact. A matching rule key identifies potentially conflicting requirements. Leave the key empty to clear the rule.</p>
    {data.suggestions?.length > 0 && <aside className="border rounded-xl p-4 space-y-2"><h2 className="font-semibold">Detected prerequisites — review before accepting</h2><p>{req.prerequisite_evidence}</p>{data.suggestions.map((r: any) => <p key={r._id}>{r.requirement_id} — {r.title}</p>)}<p>Confirm applicable IDs in the prerequisite field below. Suggestions are not applied automatically.</p></aside>}
    <form onSubmit={save} className="bg-white border rounded-xl p-6 space-y-4">
      {['key', 'value', 'condition', 'exception', 'answer_fact', 'module_category', 'assessment_topic'].map(field => <label className="block capitalize" key={field}>{field.replace(/_/g, ' ')}<Input name={field} defaultValue={req.policy_rule?.[field] || ''} /></label>)}
      <label className="block">Prerequisite requirement IDs (comma separated)<Input name="prerequisites" defaultValue={req.prerequisites.join(',')} /></label>
      <details><summary>Available approved requirements</summary><ul>{data.available.map((r: any) => <li key={r._id}>{r.requirement_id} — {r.title}</li>)}</ul></details>
      <label className="block">Review reason<Textarea name="reason" required minLength={3} /></label>
      <Button>Save reviewed rules</Button>
    </form>
  </section>;
}
