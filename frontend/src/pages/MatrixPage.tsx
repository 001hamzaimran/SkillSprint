import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router';
import { toast } from 'sonner';
import { BookOpen, Search, ArrowRight } from 'lucide-react';
import api from '@/lib/api';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Requirement {
  id: string;
  title: string;
  excerpt: string;
  obligation_level: string;
  due_stage: string;
  source_doc_id: string;
  source_section_id: string;
}

interface Role {
  id: string;
  name: string;
}

export function MatrixPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const roleIdParam = searchParams.get('role_id') || '';
  
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState(roleIdParam);
  
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch roles for the dropdown
    api.get('roles').json<{ roles: Array<{ _id: string; name: string }> }>()
      .then(data => setRoles(data.roles.map(role => ({ id: role._id, name: role.name }))))
      .catch(() => toast.error('Failed to load roles'));
  }, []);

  useEffect(() => {
    if (roleIdParam) {
      fetchMatrix(roleIdParam);
    } else {
      setRequirements([]);
    }
  }, [roleIdParam]);

  const fetchMatrix = async (roleId: string) => {
    setLoading(true);
    try {
      const data = await api.get('matrix', { searchParams: { role_id: roleId } })
        .json<{ requirements: import('@/types').Requirement[] }>();
      setRequirements(data.requirements.map(req => ({
        id: req.requirement_id, title: req.title, excerpt: req.text,
        obligation_level: req.mandatory ? 'Mandatory' : 'Optional',
        due_stage: req.due_stage, source_doc_id: req.document_id,
        source_section_id: req.section_id,
      })));
    } catch (error) {
      toast.error('Failed to load matrix');
    } finally {
      setLoading(false);
    }
  };

  const handleView = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedRole) {
      setSearchParams({ role_id: selectedRole });
    } else {
      setSearchParams({});
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <PageHeader 
          eyebrow="THE APPROVED BASELINE" 
          title="Role requirements" 
        />
        {requirements.length > 0 && (
          <Badge variant="default" className="text-sm px-3 py-1 mt-2">
            {requirements.length} requirements
          </Badge>
        )}
      </div>

      <div className="bg-paper p-4 rounded-lg border border-border">
        <form onSubmit={handleView} className="flex flex-col sm:flex-row gap-3 items-end sm:items-center">
          <div className="flex-1 w-full space-y-1">
            <label className="text-sm font-medium text-ink">Select Role</label>
            <select 
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">-- Choose a role --</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <Button type="submit" disabled={!selectedRole || loading} className="w-full sm:w-auto">
            <Search className="w-4 h-4 mr-2" /> View requirements
          </Button>
        </form>
      </div>

      {loading ? (
        <Spinner className="mx-auto mt-20" size="lg" />
      ) : !roleIdParam ? (
        <div className="text-center py-20 text-muted">
          Select a role to view its requirements matrix.
        </div>
      ) : requirements.length === 0 ? (
        <EmptyState 
          title="No requirements defined" 
          description="There are no requirements extracted for this role yet. Go to Documents to upload source policies." 
          icon={<BookOpen className="w-10 h-10 text-muted" />}
          action={
            <Link to="/documents">
              <Button>Go to Documents</Button>
            </Link>
          }
        />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-paper border-b border-border">
              <tr>
                <th className="p-4 font-medium text-ink w-1/2">Requirement</th>
                <th className="p-4 font-medium text-ink">Obligation</th>
                <th className="p-4 font-medium text-ink">Due stage</th>
                <th className="p-4 font-medium text-ink text-right">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {requirements.map(req => (
                <tr key={req.id} className="hover:bg-paper/50 align-top">
                  <td className="p-4">
                    <div className="font-semibold text-ink mb-1">{req.title}</div>
                    <div className="text-xs text-muted mb-2 font-mono">{req.id}</div>
                    <p className="text-muted line-clamp-2" title={req.excerpt}>{req.excerpt}</p>
                  </td>
                  <td className="p-4">
                    <Badge variant="default" className="bg-paper text-ink">{req.obligation_level}</Badge>
                  </td>
                  <td className="p-4 text-ink capitalize">{req.due_stage}</td>
                  <td className="p-4 text-right">
                    <Link 
                      to={`/documents/${req.source_doc_id}#${req.source_section_id}`}
                      className="text-green hover:underline inline-flex items-center gap-1 text-xs font-medium"
                    >
                      View source <ArrowRight className="w-3 h-3" />
                    </Link>
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

export default MatrixPage;
