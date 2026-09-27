import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import api from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function RecoveryPage() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [message, setMessage] = useState('');
  const [developmentLink, setDevelopmentLink] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setMessage('');
    try {
      const data = await api.post(token ? 'auth/reset-password' : 'auth/forgot-password', {
        json: token ? { token, password: form.get('password') } : { email: form.get('email') },
      }).json<{ message: string; development_reset_url?: string }>();
      setMessage(data.message); setDevelopmentLink(data.development_reset_url || '');
    } catch { setMessage('Unable to complete the request. Check the input or request a new reset link.'); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen grid place-items-center p-6 bg-paper"><section className="bg-white border rounded-xl p-8 max-w-md w-full space-y-5">
    <h1 className="text-2xl font-bold">{token ? 'Choose a new password' : 'Recover your account'}</h1>
    <form onSubmit={submit} className="space-y-4">
      <label className="block">{token ? 'New password (12–128 characters)' : 'Account email'}
        <Input name={token ? 'password' : 'email'} type={token ? 'password' : 'email'} required minLength={token ? 12 : undefined} maxLength={token ? 128 : 254} autoComplete={token ? 'new-password' : 'email'} />
      </label>
      <Button disabled={busy} type="submit">{busy ? 'Sending…' : token ? 'Update password' : 'Send reset link'}</Button>
    </form>
    {message && <p role="status">{message}</p>}
    {developmentLink && <a className="text-green underline block" href={developmentLink}>Open development reset link</a>}
    <Link className="text-green underline" to="/login">Back to sign in</Link>
  </section></main>;
}
