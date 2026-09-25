import React, { useEffect } from 'react';
import { Link } from 'react-router';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { useLearningStore } from '@/stores/learningStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, BookOpen } from 'lucide-react';

export function LearningHomePage() {
  const { user } = useAuthStore();
  const { cards, fetchLearningHome, isLoading } = useLearningStore();

  useEffect(() => {
    fetchLearningHome();
  }, [fetchLearningHome]);

  const title = user?.role === 'employee' ? 'My Sprint' : 'Learning progress';

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        eyebrow="A LITTLE PROGRESS, EVERY DAY"
        title={title} 
      />

      {(!cards || cards.length === 0) ? (
        <EmptyState 
          icon={<BookOpen className="w-10 h-10 text-muted" />}
          title="No plans assigned"
          description="There are currently no active learning plans to display."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cards.map((card) => {
            const report = card.report;
            return (
              <Card key={card.employee._id} className="flex flex-col">
                <CardHeader>
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <CardTitle className="text-lg">{card.employee.name}</CardTitle>
                      <p className="text-sm text-muted">{card.employee.role_name}</p>
                    </div>
                    {card.plan && (
                      <StatusBadge status={card.plan.status} />
                    )}
                  </div>
                </CardHeader>
                
                <CardContent className="flex-1 space-y-4">
                  {card.plan ? (
                    <>
                      <div>
                        <h4 className="font-semibold">{card.plan.content?.title || card.employee.role_name}</h4>
                        <p className="text-sm text-muted mt-1">{card.plan.content?.summary}</p>
                      </div>

                      {report && (
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Overall Progress</span>
                            <span className="font-medium">{report.percent}%</span>
                          </div>
                          <Progress value={report.percent} />
                        </div>
                      )}

                      {report && (
                        <div className="flex flex-wrap gap-2 text-sm">
                          <Badge variant="default">
                            {report.mandatory_completed} / {report.mandatory_total} Mandatory
                          </Badge>
                          {report.overdue > 0 && (
                            <Badge variant="destructive">
                              {report.overdue} Overdue
                            </Badge>
                          )}
                          {report.weak && report.weak.length > 0 && (
                            <Badge variant="warning">
                              {report.weak.length} Weak Areas
                            </Badge>
                          )}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-2 py-6">
                      <BookOpen className="h-12 w-12 text-muted/30" />
                      <p className="text-muted">No active plan assigned yet.</p>
                    </div>
                  )}
                </CardContent>

              {card.plan && (
                <CardFooter>
                  <Button asChild className="w-full">
                    <Link to={`/learning/${card.plan._id}`}>
                      Continue learning <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </CardFooter>
              )}
            </Card>
          );
        })}
        </div>
      )}
    </div>
  );
}

export default LearningHomePage;

