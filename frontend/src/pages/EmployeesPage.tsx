import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router';
import { toast } from 'sonner';
import { Users, ChevronDown, ChevronUp, UserPlus, ArrowUpRight, ArrowRight } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuthStore } from '@/stores/authStore';
import { useEmployeeStore } from '@/stores/employeeStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

const employeeSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  role_id: z.string().min(1, 'Role is required'),
  joining_date: z.string().min(1, 'Joining date is required'),
  experience: z.enum(['Beginner', 'Intermediate', 'Advanced']),
  manager_id: z.string().optional(),
  user_id: z.string().optional(),
});

type EmployeeFormData = z.infer<typeof employeeSchema>;

export function EmployeesPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { employees, roles, managers, accounts, isLoading: loading, fetchEmployees, addEmployee, generatePlan } = useEmployeeStore();
  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';
  
  const [showAddForm, setShowAddForm] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<EmployeeFormData>({
    resolver: zodResolver(employeeSchema),
  });

  useEffect(() => {
    fetchEmployees().catch(() => toast.error('Failed to load employees'));
  }, [fetchEmployees]);

  const onSubmit = async (data: EmployeeFormData) => {
    try {
      await addEmployee(data);
      toast.success('Employee added successfully');
      reset();
      setShowAddForm(false);
      fetchEmployees();
    } catch (error) {
      toast.error('Failed to add employee');
    }
  };

  const handleGeneratePlan = async (employeeId: string) => {
    try {
      const jobId = await generatePlan(employeeId);
      toast.success('Plan generation started');
      navigate(`/jobs/${jobId}`);
    } catch (error) {
      toast.error('Failed to generate plan');
    }
  };

  if (loading && employees.length === 0) {
    return <Spinner className="mx-auto mt-20" size="lg" />;
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      <PageHeader 
        eyebrow="PEOPLE FIRST" 
        title="Every person. A clear path." 
      />

      {isEditor && (
        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div 
            className="p-4 flex items-center justify-between cursor-pointer bg-paper hover:bg-gray-100 transition-colors"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            <div className="flex items-center gap-2 font-medium">
              <UserPlus className="w-4 h-4" /> Add new employee
            </div>
            {showAddForm ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
          
          {showAddForm && (
            <div className="p-6 border-t border-border">
              <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input {...register('name')} placeholder="Full name" />
                  {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="employee-role">Job role</Label>
                  <Select id="employee-role" {...register('role_id')}>
                    <option value="">Choose a role</option>
                    {roles.map(role => <option key={role._id} value={role._id}>{role.name}</option>)}
                  </Select>
                  {errors.role_id && <p className="text-sm text-red-500">{errors.role_id.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Joining Date</Label>
                  <Input type="date" {...register('joining_date')} />
                  {errors.joining_date && <p className="text-sm text-red-500">{errors.joining_date.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Experience</Label>
                  <select 
                    {...register('experience')} 
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="">Select level...</option>
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                  {errors.experience && <p className="text-sm text-red-500">{errors.experience.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="employee-manager">Manager (optional)</Label>
                  <Select id="employee-manager" {...register('manager_id')}>
                    <option value="">No manager assigned</option>
                    {managers.map(account => <option key={account._id} value={account._id}>{account.name}</option>)}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="employee-account">Employee login (optional)</Label>
                  <Select id="employee-account" {...register('user_id')}>
                    <option value="">Link an account later</option>
                    {accounts.map(account => <option key={account._id} value={account._id}>{account.name} ({account.email})</option>)}
                  </Select>
                </div>
                <div className="col-span-full pt-2">
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Adding...' : 'Add employee'}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {employees.length === 0 ? (
        <EmptyState title="No employees found" description="Add employees to start generating onboarding plans." icon={<Users className="w-10 h-10 text-muted" />} />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-paper border-b border-border">
              <tr>
                <th className="p-4 font-medium text-ink">Employee name</th>
                <th className="p-4 font-medium text-ink">Role & department</th>
                <th className="p-4 font-medium text-ink">Joining date</th>
                <th className="p-4 font-medium text-ink">Experience</th>
                <th className="p-4 font-medium text-ink text-right">Next step</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {employees.map(emp => (
                <tr key={emp._id} className="hover:bg-paper/50">
                  <td className="p-4 font-medium">{emp.name}</td>
                  <td className="p-4 text-muted">
                    {emp.role_name} ({emp.department})
                  </td>
                  <td className="p-4">{formatDate(emp.joining_date)}</td>
                  <td className="p-4">
                    <Badge variant="default">{emp.experience}</Badge>
                  </td>
                  <td className="p-4 text-right">
                    {isEditor ? (
                      <Button variant="secondary" size="sm" onClick={() => handleGeneratePlan(emp._id)} className="gap-1">
                        Generate plan <ArrowUpRight className="w-4 h-4" />
                      </Button>
                    ) : (
                      <Link to="/plans" className="text-green hover:underline inline-flex items-center gap-1 font-medium">
                        View plans <ArrowRight className="w-4 h-4" />
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default EmployeesPage;
