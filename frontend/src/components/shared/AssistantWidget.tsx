import { useEffect, useRef, useState, type FormEvent } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Link, useLocation } from 'react-router';
import { ArrowUpRight, MessageCircle, Send, Sparkles, X, RotateCcw } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { availableGuides, findGuides, type Guide } from '@/lib/assistantGuides';
import { runAssistantTool, readDocument, confirmActivation, canReadLibrary, type ToolClient, type ToolResult, type LibraryDocument, type AssistantAction } from '@/lib/assistantTools';
import api from '@/lib/api';
import mark from '@/assets/skillsprint-mark.svg';

type Exchange = { question: string; guides: Guide[]; result?: ToolResult };
const tools: ToolClient = {
  get: <T,>(path: string, signal?: AbortSignal) => api.get(path, { signal }).json<T>(),
  post: async (path, signal) => { await api.post(path, { signal, retry: 0 }); },
};

async function failureMessage(error: unknown) {
  if (error && typeof error === 'object' && 'response' in error) {
    try {
      const body = await (error as { response: Response }).response.clone().json();
      if (typeof body.detail === 'string') return body.detail;
    } catch { /* Keep a safe fallback if the response is not JSON. */ }
  }
  return error instanceof Error ? error.message : 'The request failed. Please try again.';
}

/** Keying by account prevents a previous user's conversation surviving a sign-out. */
export function AssistantWidget() {
  const user = useAuthStore(s => s.user);
  return <AssistantPanel key={`${user?._id || 'guest'}:${user?.role || 'guest'}`} role={user?.role || 'guest'} />;
}

function AssistantPanel({ role }: { role: string }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<Exchange[]>([]);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<LibraryDocument | null>(null);
  const request = useRef<AbortController | null>(null);
  const context = useRef<LibraryDocument[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const { pathname } = useLocation();
  const suggestions = availableGuides(role).filter(g => role === 'guest' || ['upload', 'generate', 'learning', 'plans'].includes(g.id)).slice(0, 3);
  const prompts = role === 'guest' ? suggestions.map(g => g.title) : [canReadLibrary(role) ? 'What is in the knowledge library?' : 'Show my plans', 'Show workspace totals', 'Help with this page'];

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }); }, [messages, open]);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener('skillsprint:help', show);
    return () => window.removeEventListener('skillsprint:help', show);
  }, []);

  function append(question: string, result?: ToolResult, guides: Guide[] = []) {
    context.current = result?.documents || [];
    setMessages(old => [...old.slice(-19), { question, guides, result }]);
  }

  async function ask(question: string) {
    const text = question.trim().slice(0, 1000);
    if (!text || request.current) return;
    const previous = messages[messages.length - 1]?.guides.map(g => g.id) || [];
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setPending(null);
    setDraft('');
    input.current?.focus();
    try {
      const result = await runAssistantTool(tools, text, role, context.current, controller.signal);
      if (!controller.signal.aborted) append(text, result || undefined, result ? [] : findGuides(text, role, pathname, previous));
    } catch (error) {
      const answer = await failureMessage(error);
      if (!controller.signal.aborted) append(text, { answer: `I couldn’t read the workspace: ${answer}`, cards: [] });
    } finally {
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }

  async function runAction(action: AssistantAction) {
    if (request.current) return;
    if (action.kind === 'activate') { setPending(action.document); return; }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setPending(null);
    try {
      const result = await readDocument(tools, role, action.document._id, controller.signal);
      if (!controller.signal.aborted) append(`Read ${action.document.title}`, result);
    } catch (error) {
      const answer = await failureMessage(error);
      if (!controller.signal.aborted) append('Read document', { answer, cards: [] });
    } finally {
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }

  async function activate() {
    if (!pending || request.current) return;
    const target = pending;
    setPending(null);
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const result = await confirmActivation(tools, role, target, controller.signal);
      if (!controller.signal.aborted) {
        append(`Activate ${target.title} v${target.version}`, result);
        window.dispatchEvent(new Event('skillsprint:documents-changed'));
      }
    } catch (error) {
      const answer = await failureMessage(error);
      if (!controller.signal.aborted) append(`Activate ${target.title}`, { answer: `Activation was not confirmed: ${answer} Check the document's current status before retrying; a network failure does not prove the server made no change.`, cards: [{ title: target.title, detail: 'Check current status', route: `/documents/${encodeURIComponent(target._id)}` }] });
    } finally {
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }

  function submit(event: FormEvent) { event.preventDefault(); ask(draft); }

  return <Dialog.Root open={open} onOpenChange={setOpen}>
    <Dialog.Trigger asChild>
      <button type="button" className="assistant-launcher fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-ink text-white px-5 py-3.5 shadow-xl hover:bg-green transition-colors" aria-label="Open Sprint Guide" title="Ask Sprint Guide">
        <MessageCircle className="h-5 w-5" aria-hidden="true" /><span className="font-semibold hidden sm:inline">Ask Sprint Guide</span><span className="h-2 w-2 rounded-full bg-lime" />
      </button>
    </Dialog.Trigger>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/20 backdrop-blur-[2px]" />
      <Dialog.Content className="fixed bottom-3 right-3 z-50 flex h-[min(680px,calc(100dvh-24px))] w-[calc(100vw-24px)] max-w-[420px] flex-col overflow-hidden rounded-3xl border border-border bg-white shadow-2xl" onOpenAutoFocus={e => { e.preventDefault(); input.current?.focus(); }}>
        <div className="bg-ink px-5 py-5 text-white flex gap-3 items-center">
          <img src={mark} alt="" className="h-11 w-11 rounded-xl border border-white/20" />
          <div className="flex-1"><Dialog.Title className="font-semibold text-lg tracking-tight">Sprint Guide</Dialog.Title><Dialog.Description className="text-xs text-white/75">Your step-by-step workspace companion</Dialog.Description></div>
          <button type="button" disabled={busy} aria-label="Clear conversation" title="Clear conversation" onClick={() => { setMessages([]); setDraft(''); setPending(null); context.current = []; input.current?.focus(); }} className="p-2 rounded-lg hover:bg-white/10 disabled:opacity-40"><RotateCcw className="h-4 w-4" /></button>
          <Dialog.Close className="p-2 rounded-lg hover:bg-white/10" aria-label="Close Sprint Guide"><X className="h-5 w-5" /></Dialog.Close>
        </div>
        <div className="border-b border-border bg-green/5 px-5 py-2 text-[11px] text-green">Live workspace tools · Role-aware · Changes need confirmation</div>
        <div className="flex-1 overflow-y-auto p-5 space-y-5 sidebar-scroll" role="log" aria-live="polite" aria-relevant="additions">
          {messages.length === 0 && <div className="space-y-4">
            <div className="w-11 h-11 flex items-center justify-center rounded-2xl bg-lime/50 text-green"><Sparkles className="h-6 w-6" /></div>
            <div><h3 className="font-semibold text-xl tracking-tight">Ask. Explore.<br />Get things done.</h3><p className="mt-2 text-sm text-muted">I can read your permitted library, show source excerpts, list plans and prepare document activation. I’ll ask before changing anything.</p></div>
            <div className="space-y-2">{prompts.map(prompt => <button key={prompt} disabled={busy} type="button" onClick={() => void ask(prompt)} className="text-left w-full flex justify-between items-center gap-2 border border-border rounded-xl px-3 py-3 text-sm hover:border-green hover:bg-green/5 disabled:opacity-50">{prompt}<ArrowUpRight className="w-4 h-4 shrink-0 text-green" /></button>)}</div>
          </div>}
          {messages.map((message, i) => <div key={i} className="space-y-3">
            <div className="ml-8 rounded-2xl rounded-br-sm bg-green text-white p-3 text-sm break-words">{message.question}</div>
            <div className="space-y-3">
              {message.result ? <>
                <p className="rounded-2xl bg-paper p-4 text-sm whitespace-pre-wrap">{message.result.answer}</p>
                {message.result.cards.map((card, j) => <div key={j} className="rounded-2xl bg-paper border border-border p-4 space-y-3">
                  <h3 className="font-semibold text-sm break-words">{card.title}</h3><p className="text-xs text-muted break-words">{card.detail}</p>
                  {card.quote && <blockquote className="border-l-2 border-green pl-3 text-sm whitespace-pre-wrap break-words">{card.quote}</blockquote>}
                  <div className="flex flex-wrap gap-2">
                    {card.actions?.map(action => <button key={action.kind} disabled={busy} type="button" onClick={() => void runAction(action)} className="rounded-lg border border-green/30 text-green px-3 py-2 text-xs font-semibold disabled:opacity-40">{action.kind === 'read' ? 'Read contents' : 'Review activation'}</button>)}
                    <Link to={card.route} onClick={() => setOpen(false)} className="inline-flex items-center gap-1.5 text-xs font-semibold text-green hover:underline">Open source<ArrowUpRight className="h-3 w-3" /></Link>
                  </div>
                </div>)}
              </> : message.guides.length === 0 ? <p className="rounded-2xl bg-paper p-4 text-sm">Try “What is in the knowledge library?”, “Read [document title]”, “Activate [document title]”, or “Show my plans”. I only support documented tools and your account’s permissions; I cannot answer assessments or perform arbitrary actions.</p> : message.guides.map(g => <div key={g.id} className="rounded-2xl bg-paper border border-border p-4">
                <h3 className="font-semibold text-sm mb-3">{g.title}</h3>
                <ol className="list-decimal pl-4 space-y-2 text-sm leading-relaxed text-muted">{g.steps.map(step => <li key={step}>{step}</li>)}</ol>
                <Link to={g.route} onClick={() => setOpen(false)} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-green hover:underline">Open page<ArrowUpRight className="h-4 w-4" /></Link>
              </div>)}
            </div>
          </div>)}
          {busy && <p role="status" className="text-sm text-green">Working with your workspace…</p>}
          <div ref={bottom} />
        </div>
        <div className="border-t border-border p-4 bg-white">
          {pending && <div className="mb-3 rounded-xl border border-amber/30 bg-amber/5 p-3 text-xs space-y-2" role="region" aria-label="Confirm document activation">
            <p className="font-semibold">Activate {pending.title}?</p><p>{pending.document_id} · v{pending.version} · Effective {pending.effective_date}</p>
            <p>This can supersede an active version and mark dependent plans as stale. Review the source before confirming.</p>
            <div className="flex gap-2"><button type="button" onClick={() => void activate()} disabled={busy} className="bg-green text-white rounded-lg px-3 py-2">Confirm activation</button><button type="button" onClick={() => setPending(null)} className="border border-border rounded-lg px-3 py-2">Cancel</button></div>
          </div>}
          <button type="button" disabled={busy} onClick={() => void ask('Help with this page')} className="text-xs text-green font-semibold mb-3 hover:underline disabled:opacity-40">Guide me on this page ↗</button>
          <form onSubmit={submit} className="flex gap-2 items-center rounded-2xl border border-border bg-paper p-2 focus-within:ring-2 focus-within:ring-green/30">
            <input ref={input} value={draft} onChange={e => setDraft(e.target.value)} maxLength={1000} aria-label="Your SkillSprint question" placeholder="How do I…" className="min-w-0 flex-1 bg-transparent px-2 py-2 text-base sm:text-sm outline-none" />
            <button type="submit" disabled={busy || !draft.trim()} aria-label="Send question" className="rounded-xl bg-green text-white p-2.5 disabled:opacity-40 hover:bg-ink"><Send className="h-4 w-4" /></button>
          </form>
          <p className="mt-2 text-[10px] text-muted text-center">No external AI sharing. Chat clears on refresh or sign-out.</p>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
