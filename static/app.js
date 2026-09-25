document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"],button:not([type])');
    if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  });
});
const job = document.querySelector('[data-job-id]');
if (job && ['queued','running'].includes(job.dataset.jobStatus)) {
  const timer = setInterval(async () => {
    try {
      const response = await fetch(`/jobs/${encodeURIComponent(job.dataset.jobId)}/status`);
      if (!response.ok || response.redirected) { clearInterval(timer); return; }
      const data = await response.json();
      if (data.status !== job.dataset.jobStatus) { clearInterval(timer); window.location.reload(); }
    } catch (_) { /* Keep a transient network failure recoverable by refresh. */ }
  }, 2500);
}
function openSource() {
  if (!window.location.hash) return;
  const source = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
  if (source && source.tagName === 'DETAILS') { source.open = true; source.scrollIntoView({block:'center'}); }
}
window.addEventListener('hashchange', openSource);
openSource();
