import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuthStore } from '@/stores/authStore';
import { useDocumentStore } from '@/stores/documentStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Spinner } from '@/components/shared/Spinner';
import * as Collapsible from '@radix-ui/react-collapsible';
import { Search, FileText, Upload, ChevronDown, ChevronUp, File as FileIcon } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const uploadSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  document_id: z.string().min(1, 'Document ID is required'),
  version: z.string().min(1, 'Version is required'),
  effective_date: z.string().min(1, 'Effective date is required'),
  category: z.string().min(1, 'Category is required'),
  role_id: z.string().optional(),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export default function DocumentsPage() {
  const { user } = useAuthStore();
  const { documents, roles, fetchDocuments, uploadDocument, isLoading } = useDocumentStore();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const isEditor = user?.role === 'admin' || user?.role === 'training_manager';

  const { register, handleSubmit, formState: { errors, isSubmitting }, reset } = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema)
  });

  useEffect(() => {
    fetchDocuments().catch(() => toast.error('Failed to load documents'));
  }, [fetchDocuments]);

  const onUpload = async (data: UploadFormValues) => {
    if (!selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', data.title);
      formData.append('document_id', data.document_id);
      formData.append('version', data.version);
      formData.append('effective_date', data.effective_date);
      formData.append('category', data.category);
      if (data.role_id) formData.append('role_id', data.role_id);
      await uploadDocument(formData);
      toast.success('Document uploaded successfully');
      setIsUploadOpen(false);
      setSelectedFile(null);
      reset();
      fetchDocuments();
    } catch (err: any) {
      toast.error(err.message || 'Failed to upload document');
    }
  };

  const filteredDocs = documents.filter(doc => 
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.document_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      <div className="flex items-start justify-between">
        <PageHeader 
          eyebrow="THE SOURCE OF TRUTH"
          title="Knowledge library"
          subtitle="Manage and explore your corporate compliance and training documents."
        >
          <span className="inline-flex items-center rounded-full bg-paper border border-border px-2.5 py-0.5 text-xs font-semibold text-muted ml-3">
            PDF + DOCX
          </span>
        </PageHeader>
      </div>

      {isEditor && (
        <Collapsible.Root open={isUploadOpen} onOpenChange={setIsUploadOpen} className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
          <Collapsible.Trigger asChild>
            <button className="w-full flex items-center justify-between p-6 hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-3">
                <Upload className="w-5 h-5 text-green" />
                <span className="font-semibold text-ink">Upload new document</span>
              </div>
              {isUploadOpen ? <ChevronUp className="w-5 h-5 text-muted" /> : <ChevronDown className="w-5 h-5 text-muted" />}
            </button>
          </Collapsible.Trigger>
          <Collapsible.Content>
            <div className="p-6 border-t border-border bg-slate-50/50">
              <form onSubmit={handleSubmit(onUpload)} className="space-y-6 max-w-3xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">Title</label>
                    <Input {...register('title')} placeholder="Code of Conduct" />
                    {errors.title && <p className="text-xs text-amber">{errors.title.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">Document ID</label>
                    <Input {...register('document_id')} placeholder="POL-001" />
                    {errors.document_id && <p className="text-xs text-amber">{errors.document_id.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">Version</label>
                    <Input {...register('version')} placeholder="1.0" />
                    {errors.version && <p className="text-xs text-amber">{errors.version.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">Effective Date</label>
                    <Input type="date" {...register('effective_date')} />
                    {errors.effective_date && <p className="text-xs text-amber">{errors.effective_date.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">Category</label>
                    <select {...register('category')} className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green">
                      <option value="">Select category...</option>
                      {['Policy', 'SOP', 'Role description', 'FAQ', 'Other'].map(category => <option key={category} value={category}>{category}</option>)}
                    </select>
                    {errors.category && <p className="text-xs text-amber">{errors.category.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="document-role" className="text-sm font-medium text-ink">Applies to</label>
                    <select id="document-role" {...register('role_id')} className="w-full h-10 rounded-md border border-border bg-white px-3 text-sm">
                      <option value="">All roles (company-wide)</option>
                      {roles.map(role => <option key={role._id} value={role._id}>{role.name}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-ink">File (PDF or DOCX)</label>
                    <Input 
                      type="file" 
                      accept=".pdf,.docx" 
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    />
                  </div>
                </div>
                <div className="flex justify-end pt-4">
                  <Button type="submit" disabled={isSubmitting || !selectedFile} className="bg-green text-white">
                    {isSubmitting ? <Spinner className="w-4 h-4 mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
                    Upload Document
                  </Button>
                </div>
              </form>
            </div>
          </Collapsible.Content>
        </Collapsible.Root>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
        <Input 
          className="pl-10 h-12 bg-white border-border shadow-sm text-base" 
          placeholder="Search by title or ID..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {isLoading && documents.length === 0 ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : filteredDocs.length === 0 ? (
        <div className="text-center py-16 bg-white border border-border rounded-xl">
          <FileText className="w-12 h-12 text-muted mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium text-ink mb-1">No documents found</h3>
          <p className="text-muted">Upload some documents to get started or try a different search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocs.map(doc => (
            <div 
              key={doc._id}
              onClick={() => navigate(`/documents/${doc._id}`)}
              className="bg-white border border-border rounded-xl p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer flex flex-col group"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2.5 rounded-lg bg-slate-50 text-muted group-hover:text-green group-hover:bg-green/10 transition-colors">
                  <FileIcon className="w-6 h-6" />
                </div>
                <StatusBadge status={doc.status as any} />
              </div>
              <h3 className="font-bold text-ink text-lg mb-1 line-clamp-2">{doc.title}</h3>
              <p className="text-sm font-mono text-muted mb-4">{doc.document_id} v{doc.version}</p>
              
              <div className="mt-auto pt-4 border-t border-border/50 flex justify-between items-center text-sm">
                <span className="text-muted capitalize">{doc.category}</span>
                <span className="text-muted">{formatDate(doc.effective_date)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
