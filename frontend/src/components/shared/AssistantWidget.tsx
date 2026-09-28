import { useEffect, useRef, useState, type FormEvent } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Link, useLocation } from 'react-router';
import { ArrowUpRight, MessageCircle, Send, Sparkles, X, RotateCcw } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { availableGuides, findGuides, type Guide } from '@/lib/assistantGuides';
import mark from '@/assets/skillsprint-mark.svg';

type Exchange = { question: string; guides: Guide[] };

/** Keying by account prevents a previous user's conversation surviving a sign-out. */
export function AssistantWidget() {
  const user = useAuthStore(s => s.user);
  return <AssistantPanel key={user?._id || 'guest'} role={user?.role || 'guest'} />;
}

function AssistantPanel({ role }: { role: string }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<Exchange[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const { pathname } = useLocation();
  const suggestions = availableGuides(role).filter(g => role === 'guest' || ['upload', 'generate', 'learning', 'plans'].includes(g.id)).slice(0, 3);

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }); }, [messages, open]);
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener('skillsprint:help', show);
    return () => window.removeEventListener('skillsprint:help', show);
  }, []);

  function ask(question: string) {
    const text = question.trim().slice(0, 1000);
    if (!text) return;
    const previous = messages[messages.length - 1]?.guides.map(g => g.id) || [];
    setMessages(old => [...old.slice(-19), { question: text, guides: findGuides(text, role, pathname, previous) }]);
    setDraft('');
    input.current?.focus();
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
          <button type="button" aria-label="Clear conversation" title="Clear conversation" onClick={() => { setMessages([]); setDraft(''); input.current?.focus(); }} className="p-2 rounded-lg hover:bg-white/10"><RotateCcw className="h-4 w-4" /></button>
          <Dialog.Close className="p-2 rounded-lg hover:bg-white/10" aria-label="Close Sprint Guide"><X className="h-5 w-5" /></Dialog.Close>
        </div>
        <div className="border-b border-border bg-green/5 px-5 py-2 text-[11px] text-green">Local help · No messages sent to AI services · No automatic changes</div>
        <div className="flex-1 overflow-y-auto p-5 space-y-5 sidebar-scroll" role="log" aria-live="polite" aria-relevant="additions">
          {messages.length === 0 && <div className="space-y-4">
            <div className="w-11 h-11 flex items-center justify-center rounded-2xl bg-lime/50 text-green"><Sparkles className="h-6 w-6" /></div>
            <div><h3 className="font-semibold text-xl tracking-tight">A little guidance.<br />A confident next step.</h3><p className="mt-2 text-sm text-muted">Ask how to use SkillSprint, or choose a task below. I’ll show documented steps and links for your role.</p></div>
            <div className="space-y-2">{suggestions.map(g => <button key={g.id} type="button" onClick={() => ask(g.title)} className="text-left w-full flex justify-between items-center gap-2 border border-border rounded-xl px-3 py-3 text-sm hover:border-green hover:bg-green/5">{g.title}<ArrowUpRight className="w-4 h-4 shrink-0 text-green" /></button>)}</div>
          </div>}
          {messages.map((message, i) => <div key={i} className="space-y-3">
            <div className="ml-8 rounded-2xl rounded-br-sm bg-green text-white p-3 text-sm break-words">{message.question}</div>
            <div className="space-y-3">
              {message.guides.length === 0 ? <p className="rounded-2xl bg-paper p-4 text-sm">I can help with SkillSprint’s documented features, but I don’t access private records or answer assessments. Try “How do I find a plan?” or “Help with this page.” If a feature isn’t available to your role, contact your administrator.</p> : message.guides.map(g => <div key={g.id} className="rounded-2xl bg-paper border border-border p-4">
                <h3 className="font-semibold text-sm mb-3">{g.title}</h3>
                <ol className="list-decimal pl-4 space-y-2 text-sm leading-relaxed text-muted">{g.steps.map(step => <li key={step}>{step}</li>)}</ol>
                <Link to={g.route} onClick={() => setOpen(false)} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-green hover:underline">Open page<ArrowUpRight className="h-4 w-4" /></Link>
              </div>)}
            </div>
          </div>)}
          <div ref={bottom} />
        </div>
        <div className="border-t border-border p-4 bg-white">
          <button type="button" onClick={() => ask('Help with this page')} className="text-xs text-green font-semibold mb-3 hover:underline">Guide me on this page ↗</button>
          <form onSubmit={submit} className="flex gap-2 items-center rounded-2xl border border-border bg-paper p-2 focus-within:ring-2 focus-within:ring-green/30">
            <input ref={input} value={draft} onChange={e => setDraft(e.target.value)} maxLength={1000} aria-label="Your SkillSprint question" placeholder="How do I…" className="min-w-0 flex-1 bg-transparent px-2 py-2 text-base sm:text-sm outline-none" />
            <button type="submit" disabled={!draft.trim()} aria-label="Send question" className="rounded-xl bg-green text-white p-2.5 disabled:opacity-40 hover:bg-ink"><Send className="h-4 w-4" /></button>
          </form>
          <p className="mt-2 text-[10px] text-muted text-center">Don’t share passwords or personal details. Chat clears on refresh.</p>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
