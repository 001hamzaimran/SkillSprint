import { useEffect } from 'react';
import { Link } from 'react-router';
import { formatDateTime } from '@/lib/utils';
import { useLearningStore } from '@/stores/learningStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, CheckSquare } from 'lucide-react';

export function AssessmentsPage() {
  const { submissions, assessmentEmployees, fetchAssessments, isLoading } = useLearningStore();

  useEffect(() => {
    fetchAssessments();
  }, [fetchAssessments]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader 
          eyebrow="THOUGHTFUL FEEDBACK"
          title="Assessments"
          subtitle="Grade practical work against rubric criteria (80% to pass)"
        />
        {submissions && submissions.length > 0 && (
          <Badge variant="warning" className="text-sm px-3 py-1 mt-2">
            {submissions.length} Pending
          </Badge>
        )}
      </div>

      {!submissions || submissions.length === 0 ? (
        <EmptyState 
          icon={<CheckSquare className="w-10 h-10 text-muted" />}
          title="All caught up"
          description="No pending practical submissions awaiting review."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {submissions.map((sub) => {
            const employee = assessmentEmployees[sub.employee_id];
            return (
              <Card key={sub._id} className="flex flex-col">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">{employee?.name || 'Employee'}</CardTitle>
                      <CardDescription>{employee?.role_name || ''}</CardDescription>
                    </div>
                    <Badge variant="warning">Pending</Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 space-y-4">
                  <div>
                    <p className="text-sm font-medium text-muted mb-1">Requirement ID</p>
                    <p className="font-mono text-sm">{sub.requirement_id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted mb-1">Submitted Time</p>
                    <p className="text-sm">{formatDateTime(sub.created_at)}</p>
                  </div>
                </CardContent>
                <div className="p-6 pt-0 mt-auto">
                  <Button asChild className="w-full">
                    <Link to={`/learning/${sub.plan_id}#${sub.requirement_id}`}>
                      Review work <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
export default AssessmentsPage;
