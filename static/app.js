document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"],button:not([type])');
    if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  });
});
document.querySelectorAll('[data-password-toggle]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Hide' : 'Show';
    button.setAttribute('aria-label', `${show ? 'Hide' : 'Show'} password`);
  });
});
const navToggle = document.querySelector('.nav-toggle');
const navigation = document.getElementById('main-navigation');
if (navToggle && navigation) {
  navToggle.addEventListener('click', () => {
    const open = navToggle.getAttribute('aria-expanded') !== 'true';
    navToggle.setAttribute('aria-expanded', String(open));
    navigation.classList.toggle('open', open);
  });
}
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
