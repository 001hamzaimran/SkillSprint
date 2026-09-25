export function Topbar() {
  return (
    <header className="min-h-[74px] flex flex-wrap gap-3 items-center justify-between px-4 md:px-8 py-3 border-b border-border bg-surface">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted">Learning & development /</span>
        <span className="font-medium text-ink">Workspace</span>
      </div>
      <div className="flex items-center">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-paper rounded-full border border-border text-sm font-medium text-ink">
          <div className="w-2 h-2 rounded-full bg-green"></div>
          AsterBridge Delivery Services
        </div>
      </div>
    </header>
  );
}
