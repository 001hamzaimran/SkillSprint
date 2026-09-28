/** Small, explicit tool set. Document text is data, never executable instructions. */
export type LibraryDocument = { _id: string; document_id: string; title: string; version: string; status: string; category: string; effective_date: string; suspicious: boolean };
export type Source = { section_id: string; heading?: string; text: string; suspicious?: boolean };
export type AssistantAction = { kind: 'read' | 'activate'; document: LibraryDocument };
export type ResultCard = { title: string; detail: string; route: string; quote?: string; actions?: AssistantAction[] };
export type ToolResult = { answer: string; cards: ResultCard[]; documents?: LibraryDocument[] };
export type ToolClient = { get<T>(path: string, signal?: AbortSignal): Promise<T>; post(path: string, signal?: AbortSignal): Promise<void> };
export const canReadLibrary = (role: string) => ['admin', 'reviewer', 'training_manager'].includes(role);
export const canActivate = (role: string) => ['admin', 'reviewer'].includes(role);
const documentPath = (id: string) => `documents/${encodeURIComponent(id)}`;
const documentRoute = (id: string) => `/${documentPath(id)}`;
const normalized = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

export function matchDocuments(message: string, documents: LibraryDocument[]) {
  const text = normalized(message);
  const exact = documents.filter(d => [d.title, d.document_id, d._id].some(value => text.includes(normalized(value))));
  if (exact.length) return exact;
  const stop = new Set('what which are is in the my our a an of to for about tell me show list library knowledge document documents policy policies please activate enable make active read summarize summarise summary explain contains does it this that one'.split(' '));
  const words = text.split(' ').filter(w => w.length > 2 && !stop.has(w));
  return documents.filter(d => words.some(w => normalized(`${d.title} ${d.document_id}`).includes(w)));
}

function card(document: LibraryDocument, role: string, activation = false): ResultCard {
  const actions: AssistantAction[] = [{ kind: 'read', document }];
  if (canActivate(role) && document.status !== 'active' && !document.suspicious) actions.push({ kind: 'activate', document });
  return { title: document.title, detail: `${document.document_id} · v${document.version} · ${document.status} · ${document.category} · Effective ${document.effective_date}${document.suspicious ? ' · Quarantined' : ''}`, route: documentRoute(document._id), actions: activation ? actions.filter(a => a.kind === 'activate') : actions };
}

export async function readDocument(client: ToolClient, role: string, id: string, signal?: AbortSignal): Promise<ToolResult> {
  if (!canReadLibrary(role)) throw new Error('Your account does not have access to the knowledge library.');
  const data = await client.get<{ document: LibraryDocument; sections: Source[] }>(documentPath(id), signal);
  if (data.document.suspicious) return { answer: 'This document is quarantined. Its content cannot be used as trusted guidance. Ask an administrator to review the source.', cards: [card(data.document, role)], documents: [data.document] };
  const sections = data.sections.filter(s => !s.suspicious);
  return {
    answer: `“${data.document.title}” contains ${sections.length} readable source sections. Below are verbatim excerpts from the first ${Math.min(sections.length, 5)} sections, not an AI summary or approval. Open the source for full context.${sections.length ? '' : ' No readable sections are available yet.'}`,
    documents: [data.document],
    cards: [card(data.document, role), ...sections.slice(0, 5).map(s => ({ title: s.heading || s.section_id, detail: `Source: ${data.document.document_id} · ${s.section_id}`, route: `${documentRoute(id)}#${encodeURIComponent(s.section_id)}`, quote: s.text.slice(0, 1200) + (s.text.length > 1200 ? '… [excerpt truncated]' : '') }))],
  };
}

/** Resolves supported requests. Reads only; mutations live exclusively in confirmActivation. */
export async function runAssistantTool(client: ToolClient, message: string, role: string, previous: LibraryDocument[] = [], signal?: AbortSignal): Promise<ToolResult | null> {
  if (role === 'guest') return null;
  const text = message.toLowerCase();
  if (/\b(how|guide|steps)\b/.test(text) && !/\b(what|list|show)\b/.test(text)) return null;
  const activation = /\b(activate|make active)\b/.test(text);
  const reading = /\b(read|summari[sz]e|summary|contents?|contains|inside|explain)\b/.test(text);
  const library = /\b(library|documents?|polic(?:y|ies)|pdf|docx)\b/.test(text) || activation || (reading && previous.length > 0);
  if (library) {
    if (!canReadLibrary(role)) return { answer: 'Your account cannot access the knowledge library. I can still help you find your permitted onboarding plans. Contact your administrator if you need source access.', cards: [] };
    if (activation && !canActivate(role)) return { answer: 'Only administrators and reviewers can activate documents. Your role can view the library but cannot perform this action.', cards: [] };
    const { documents } = await client.get<{ documents: LibraryDocument[] }>('documents', signal);
    let matches = matchDocuments(message, documents);
    if (!matches.length && /\b(this|that|it)\b/.test(text) && previous.length === 1) matches = documents.filter(d => d._id === previous[0]._id);
    const generic = /^(what( is|'s|s| are)? (in |inside )?(the |our |my )?(knowledge )?library[?.!]*|show (me )?(the )?(knowledge )?library[?.!]*|list (all )?(documents|policies)[?.!]*)$/i.test(message.trim());
    const selection = matches.length ? matches : generic ? documents : [];
    if (reading && !activation && matches.length === 1) return readDocument(client, role, matches[0]._id, signal);
    if (activation && matches.length === 1 && matches[0].status === 'active') return { answer: `“${matches[0].title}” v${matches[0].version} is already active. Nothing was changed.`, cards: [card(matches[0], role)], documents: matches };
    if (activation && matches.length === 1 && matches[0].suspicious) return { answer: 'This document is quarantined and cannot be activated. Upload a corrected source through the normal review workflow.', cards: [card(matches[0], role)], documents: matches };
    const candidates = selection.length ? selection : activation && /^(please )?activate (a |the )?document[?.!]*$/i.test(message.trim()) ? documents.filter(d => d.status !== 'active') : [];
    const answer = activation
      ? 'Nothing has been changed. Select the exact document/version below, then review and confirm activation. Activation may supersede an older version and mark dependent plans as stale.'
      : `${candidates.length} document${candidates.length === 1 ? '' : 's'} ${matches.length ? 'matched' : 'returned from the library'}${documents.length === 100 ? ' (the library API returns at most 100 recent documents)' : ''}. ${candidates.length ? `Showing ${Math.min(candidates.length, 20)} below. Choose Read contents to inspect source excerpts.` : 'Try a document title or ID, or ask “What is in the knowledge library?”'}`;
    return { answer: candidates.length || !activation ? answer : 'No matching inactive document was found. Nothing was changed. Try its exact title or ID.', cards: candidates.slice(0, 20).map(d => card(d, role, activation)), documents: candidates };
  }
  if (/\b(plans?|onboarding)\b/.test(text) && /\b(list|show|status|what|which|my)\b/.test(text)) {
    const { plans } = await client.get<{ plans: { _id: string; status: string; content: { title: string } }[] }>('plans', signal);
    return { answer: `${plans.length} plans returned within your account's scope (up to 100). Showing ${Math.min(plans.length, 20)}.`, cards: plans.slice(0, 20).map(p => ({ title: p.content.title, detail: `Status: ${p.status}`, route: `/plans/${encodeURIComponent(p._id)}` })) };
  }
  if (/\b(overview|dashboard|workspace totals|how many)\b/.test(text)) {
    const { stats } = await client.get<{ stats: { employees: number; documents?: number; approved?: number; plans: number } }>('dashboard', signal);
    return { answer: `Your workspace view: ${stats.employees} people, ${stats.plans} plans${stats.documents === undefined ? '' : `, ${stats.documents} documents`}${stats.approved === undefined ? '' : `, ${stats.approved} approved requirements`}. These are live totals within the API's permitted scope.`, cards: [] };
  }
  return null;
}

/** Explicit confirmation is required by the UI. Recheck target and permissions before POST. */
export async function confirmActivation(client: ToolClient, role: string, expected: LibraryDocument, signal?: AbortSignal) {
  if (!canActivate(role)) throw new Error('Only administrators and reviewers can activate documents.');
  const { document } = await client.get<{ document: LibraryDocument }>(documentPath(expected._id), signal);
  if (['_id', 'document_id', 'title', 'version', 'effective_date', 'status', 'suspicious'].some(k => document[k as keyof LibraryDocument] !== expected[k as keyof LibraryDocument])) throw new Error('The document changed since you selected it. Ask again and review the latest version.');
  if (document.suspicious || document.status === 'active') throw new Error('This document is quarantined or already active. Refresh its status before continuing.');
  await client.post(`${documentPath(document._id)}/activate`, signal);
  return { answer: `Activated “${document.title}” v${document.version}. The server recorded the decision in the activity trail. Review any plans affected by superseded sources.`, cards: [{ title: document.title, detail: 'Activation confirmed by the server', route: documentRoute(document._id) }] } satisfies ToolResult;
}
