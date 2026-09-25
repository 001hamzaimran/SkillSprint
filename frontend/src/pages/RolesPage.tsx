import { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { toast } from 'sonner';
import { Briefcase, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

const roleSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  department: z.string().min(1, 'Department is required'),
  description: z.string().min(1, 'Description is required'),
});

type RoleFormData = z.infer<typeof roleSchema>;

interface Role {
  _id: string;
  name: string;
  department: string;
  description: string;
}

export function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
  });

  const fetchRoles = async () => {
    try {
      const data = await api.get('roles').json<{ roles: Role[] }>();
      setRoles(data.roles || []);
    } catch (error) {
      toast.error('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  const onSubmit = async (data: RoleFormData) => {
    try {
      await api.post('roles', { json: data });
      toast.success('Role created successfully');
      reset();
      fetchRoles();
    } catch (error) {
      toast.error('Failed to create role');
    }
  };

  if (loading) {
    return <Spinner className="mx-auto mt-20" size="lg" />;
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      <PageHeader 
        eyebrow="MADE FOR EACH ROLE" 
        title="Job roles" 
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          {roles.length === 0 ? (
            <EmptyState title="No roles found" description="Create a role to get started." icon={<Briefcase className="w-10 h-10 text-muted" />} />
          ) : (
            roles.map(role => (
              <div key={role._id} className="p-6 bg-white rounded-lg border border-border shadow-sm flex items-start gap-4">
                <div className="bg-paper p-3 rounded-md">
                  <Briefcase className="w-5 h-5 text-ink" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-lg text-ink">{role.name}</h3>
                      <span className="text-sm text-muted">{role.department}</span>
                    </div>
                    <Link 
                      to={`/matrix?role_id=${role._id}`}
                      className="text-sm font-medium text-green hover:underline flex items-center gap-1"
                    >
                      Requirements <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                  <p className="mt-2 text-ink text-sm">{role.description}</p>
                </div>
              </div>
            ))
          )}
        </div>

        {isEditor && (
          <div>
            <div className="bg-paper p-6 rounded-lg border border-border sticky top-6">
              <h3 className="font-semibold text-lg mb-4">Create new role</h3>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Role Name</Label>
                  <Input id="name" {...register('name')} placeholder="e.g. Frontend Engineer" />
                  {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Input id="department" {...register('department')} placeholder="e.g. Engineering" />
                  {errors.department && <p className="text-sm text-red-500">{errors.department.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea id="description" {...register('description')} placeholder="Role responsibilities..." rows={4} />
                  {errors.description && <p className="text-sm text-red-500">{errors.description.message}</p>}
                </div>
                <Button type="submit" disabled={isSubmitting} className="w-full">
                  {isSubmitting ? 'Creating...' : 'Create role'}
                </Button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RolesPage;

