import React, { useState, useEffect } from 'react';
import { Users, User } from 'lucide-react';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';

import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

export function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { user } = useAuthStore();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'employee',
  });

  const fetchUsers = async () => {
    try {
      const data = await api.get('users').json<{ users: any[] }>();
      setUsers(data.users || []);
    } catch (err) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password.length < 12) {
      toast.error('Password must be at least 12 characters');
      return;
    }

    setSubmitting(true);
    try {
      await api.post('users', { json: formData });
      toast.success('Account created successfully');
      setFormData({
        name: '',
        email: '',
        password: '',
        role: 'employee',
      });
      fetchUsers();
    } catch (err: any) {
      toast.error(err.message || 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'admin': return 'destructive';
      case 'training_manager': return 'warning';
      case 'reviewer': return 'warning';
      case 'manager': return 'default';
      default: return 'success';
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        eyebrow="THE RIGHT ACCESS" 
        title="Workspace accounts"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-medium text-lg flex items-center gap-2">
            <Users className="w-5 h-5" /> Account roster
          </h3>
          
          {loading ? (
            <div className="flex justify-center p-8"><Spinner size="lg" /></div>
          ) : users.length === 0 ? (
            <EmptyState
              icon={<Users className="w-10 h-10 text-muted" />}
              title="No users found"
              description="No user accounts are currently registered."
            />
          ) : (
            <div className="border rounded-md bg-white overflow-hidden">
              <ul className="divide-y">
                {users.map((u, i) => (
                  <li key={i} className="p-4 flex items-center justify-between hover:bg-muted/5">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold">
                        {u.name?.charAt(0).toUpperCase() || <User className="w-5 h-5" />}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={getRoleBadgeVariant(u.role)}>
                        {u.role.replace('_', ' ')}
                      </Badge>
                      <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Active
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Create new account</CardTitle>
              <CardDescription>Add a new team member to this workspace.</CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-ink">Full name</label>
                  <Input 
                    required 
                    placeholder="e.g. Jane Doe"
                    value={formData.name}
                    onChange={e => setFormData({...formData, name: e.target.value})}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-ink">Email address</label>
                  <Input 
                    required 
                    type="email"
                    placeholder="jane@company.com"
                    value={formData.email}
                    onChange={e => setFormData({...formData, email: e.target.value})}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-ink">Password</label>
                  <Input 
                    required 
                    type="password"
                    placeholder="••••••••••••"
                    value={formData.password}
                    onChange={e => setFormData({...formData, password: e.target.value})}
                  />
                  <p className="text-[10px] text-muted">Minimum 12 characters</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-ink">Role</label>
                  <Select 
                    value={formData.role} 
                    onChange={e => setFormData({...formData, role: e.target.value})}
                  >
                    <option value="employee">Employee</option>
                    <option value="manager">Manager</option>
                    <option value="training_manager">Training Manager</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="admin">Admin</option>
                  </Select>
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? <Spinner className="mr-2" size="sm" /> : null}
                  Create account
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default UsersPage;
