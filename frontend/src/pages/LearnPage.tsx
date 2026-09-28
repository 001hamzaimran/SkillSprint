import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { cn, formatDateTime } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { useLearningStore } from '@/stores/learningStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Spinner } from '@/components/shared/Spinner';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { StatCard } from '@/components/shared/StatCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, AlertCircle, CheckCircle2, Clock, XCircle, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import type { ProgressReport } from '@/types';
import { useHashTarget } from '@/lib/useHashTarget';

export function LearnPage() {
  const { planId } = useParams<{ planId: string }>();
  const { user } = useAuthStore();
  const { 
    currentPlan: plan, 
    currentEmployee: employee,
    report,
    active: isActive,
    isLearner,
    fetchLearnWorkspace, 
    isLoading,
    saveProgress,
    submitQuiz,
    submitPractical,
    gradeSubmission,
  } = useLearningStore();
  useHashTarget(!isLoading && !!report && plan?._id === planId);

  useEffect(() => {
    if (planId) {
      fetchLearnWorkspace(planId);
    }
  }, [planId, fetchLearnWorkspace]);

  if (isLoading || !plan || !report) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const isReviewerOrManager = user?.role === 'reviewer' || user?.role === 'manager' || user?.role === 'admin';

  return (
    <div className="space-y-8 pb-12">
      <div className="space-y-4">
        <Link to="/learning" className="inline-flex items-center text-sm font-medium text-muted hover:text-ink transition-colors">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to sprint
        </Link>
        <PageHeader 
          eyebrow={`${employee?.name || 'Learner'} · ${employee?.role_name || ''}`}
          title={plan.content?.title || 'Learning Plan'}
          subtitle={plan.content?.summary}
        />
      </div>

      {!isActive && (
        <div className="bg-amber/10 border border-amber/30 p-4 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-amber shrink-0" />
          <p className="text-sm text-amber font-medium">
            This is not the current active published plan. Displayed in read-only mode.
          </p>
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          label="Overall Completion" 
          value={`${report.percent}%`} 
          subtext={`${report.completed} of ${report.total} modules done`}
        />
        <StatCard 
          label="Mandatory Requirements" 
          value={`${report.mandatory_completed}/${report.mandatory_total}`} 
          subtext={report.mandatory_complete ? 'All mandatory items completed' : 'In progress'}
        />
        <StatCard 
          label="Overdue Modules" 
          value={report.overdue} 
          subtext={report.overdue > 0 ? 'Requires attention' : 'On schedule'}
        />
      </div>

      {/* Stage Milestones */}
      {report.milestones && report.milestones.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Sprint Milestones</CardTitle>
            <CardDescription>Progress across onboarding timeline stages</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {report.milestones.map((m) => {
              const pct = m.total > 0 ? Math.round((m.complete / m.total) * 100) : 0;
              return (
                <div key={m.stage} className="p-4 rounded-lg border border-border bg-paper space-y-2">
                  <div className="flex justify-between items-center text-sm font-medium">
                    <span>{m.stage}</span>
                    <span className="text-muted">{m.complete}/{m.total}</span>
                  </div>
                  <Progress value={pct} />
                  <p className="text-xs text-muted text-right">{pct}% done</p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Weak Areas Banner */}
      {report.weak && report.weak.length > 0 && (
        <div className="bg-amber/10 border border-amber/20 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-amber font-semibold">
            <AlertCircle className="h-5 w-5" />
            <span>Areas to Revisit ({report.weak.length})</span>
          </div>
          <p className="text-sm text-amber/80">
            You scored below passing on quizzes for these modules. Review the material:
          </p>
          <div className="flex flex-wrap gap-2">
            {report.weak.map((w, idx) => (
              <a 
                key={idx} 
                href={`#${w.item.requirement_id}`}
                className="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium bg-amber/20 text-amber hover:bg-amber/30 transition-colors"
              >
                {w.item.module_title}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Learning Items */}
      <div className="space-y-6">
        <h2 className="text-2xl font-bold tracking-tight text-ink">Learning Modules</h2>
        
        {report.rows.map((row) => (
          <ModuleCard 
            key={row.item.requirement_id}
            row={row}
            planId={plan._id}
            isActive={isActive}
            isLearner={isLearner}
            isReviewerOrManager={isReviewerOrManager}
            onSaveProgress={saveProgress}
            onSubmitQuiz={submitQuiz}
            onSubmitPractical={submitPractical}
            onGrade={gradeSubmission}
            onRefresh={() => fetchLearnWorkspace(plan._id)}
          />
        ))}
      </div>
    </div>
  );
}

interface ModuleCardProps {
  row: ProgressReport['rows'][0];
  planId: string;
  isActive: boolean;
  isLearner: boolean;
  isReviewerOrManager: boolean;
  onSaveProgress: (planId: string, reqId: string, data: Record<string, unknown>) => Promise<void>;
  onSubmitQuiz: (planId: string, reqId: string, answer: number | number[]) => Promise<void>;
  onSubmitPractical: (planId: string, reqId: string, data: Record<string, string>) => Promise<void>;
  onGrade: (submissionId: string, data: Record<string, unknown>) => Promise<void>;
  onRefresh: () => void;
}

function ModuleCard({
  row,
  planId,
  isActive,
  isLearner,
  isReviewerOrManager,
  onSaveProgress,
  onSubmitQuiz,
  onSubmitPractical,
  onGrade,
  onRefresh,
}: ModuleCardProps) {
  const { item, saved: progress, quiz_passed, quiz_attempts, practical_passed, latest_submission, complete, overdue, blocked_by } = row;
  
  const [expandedEvidence, setExpandedEvidence] = useState(false);
  const [isLessonRead, setIsLessonRead] = useState(progress?.lesson_read || false);
  const [checklist, setChecklist] = useState<boolean[]>(() => {
    const checked = progress?.checked || [];
    return (item.checklist || []).map((_, i) => checked.includes(i));
  });
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<number[]>([]);
  const multiple = item.quiz?.question_type === 'multiple_response';
  const [scenarioResp, setScenarioResp] = useState('');
  const [practicalResp, setPracticalResp] = useState('');
  const [scores, setScores] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState('');

  const isBlocked = blocked_by && blocked_by.length > 0;

  const handleSaveProgress = async () => {
    try {
      const checkedIndices = checklist.map((val, idx) => (val ? idx : -1)).filter((idx) => idx !== -1);
      await onSaveProgress(planId, item.requirement_id, {
        lesson_read: isLessonRead,
        checked: checkedIndices,
      });
      toast.success('Progress saved');
      onRefresh();
    } catch {
      toast.error('Failed to save progress');
    }
  };

  const handleCheckAnswer = async () => {
    if (multiple ? selectedAnswers.length === 0 : selectedAnswer === null) {
      toast.error('Please select an answer');
      return;
    }
    try {
      await onSubmitQuiz(planId, item.requirement_id, multiple ? selectedAnswers : selectedAnswer!);
      onRefresh();
    } catch {
      toast.error('Failed to submit answer');
    }
  };

  const handleSubmitPractical = async () => {
    if (!scenarioResp.trim() || !practicalResp.trim()) {
      toast.error('Please fill in both scenario and practical responses');
      return;
    }
    try {
      await onSubmitPractical(planId, item.requirement_id, {
        scenario_response: scenarioResp,
        practical_response: practicalResp,
      });
      toast.success('Submission sent for review');
      setScenarioResp('');
      setPracticalResp('');
      onRefresh();
    } catch {
      toast.error('Failed to submit assignment');
    }
  };

  const handleGradeSubmission = async (submissionId: string) => {
    try {
      await onGrade(submissionId, {
        ...scores,
        feedback,
      });
      toast.success('Submission graded');
      onRefresh();
    } catch {
      toast.error('Failed to grade submission');
    }
  };

  return (
    <Card id={item.requirement_id} className={cn("scroll-m-20", isBlocked && "opacity-75")}>
      <CardHeader className="bg-paper border-b border-border">
        <div className="flex flex-wrap gap-2 mb-3">
          <Badge variant="default">{item.stage}</Badge>
          <Badge variant={item.mandatory ? 'warning' : 'default'}>
            {item.mandatory ? 'Mandatory' : 'Optional'}
          </Badge>
          <StatusBadge status={complete ? 'completed' : overdue ? 'failed' : 'in_progress'} />
        </div>
        <CardTitle className="text-xl">{item.module_title}</CardTitle>
        <CardDescription className="text-base text-ink mt-2">
          {item.learning_objective}
        </CardDescription>
        <div className="flex items-center gap-4 text-sm text-muted mt-4">
          <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> {item.estimated_minutes} mins</span>
        </div>
      </CardHeader>
      
      <CardContent className="p-6">
        {isBlocked && (
          <div className="mb-6 bg-amber/10 border border-amber/20 p-4 rounded-md flex gap-3">
            <AlertCircle className="h-5 w-5 text-amber shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-amber">Prerequisite Blocked</h4>
              <p className="text-sm text-amber/80 mt-1">
                You must complete: {blocked_by.join(', ')} before starting this module.
              </p>
            </div>
          </div>
        )}

        <div className="mb-8 max-w-none text-ink space-y-4">
          <p className="whitespace-pre-wrap leading-relaxed">{item.lesson}</p>
          {item.source_quote && (
            <div className="mt-4">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setExpandedEvidence(!expandedEvidence)}
                className="text-muted hover:text-ink px-0"
              >
                {expandedEvidence ? <ChevronUp className="h-4 w-4 mr-2" /> : <ChevronDown className="h-4 w-4 mr-2" />}
                Source material quote
              </Button>
              {expandedEvidence && (
                <div className="mt-2 pl-4 border-l-2 border-border italic text-muted text-sm">
                  "{item.source_quote}"
                </div>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Column 1: Checklist & Quiz */}
          <div className="space-y-8">
            <section className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green" /> Progress Checklist
              </h3>
              <div className="space-y-3">
                <label className="flex items-start space-x-3 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={isLessonRead} 
                    onChange={(e) => setIsLessonRead(e.target.checked)}
                    disabled={isBlocked || !isActive || !isLearner}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-green focus:ring-green"
                  />
                  <span className="text-sm text-ink">I have read the lesson materials</span>
                </label>
                {item.checklist && item.checklist.map((checkItem, idx) => (
                  <label key={idx} className="flex items-start space-x-3 cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={checklist[idx] || false} 
                      onChange={(e) => {
                        const newC = [...checklist];
                        newC[idx] = e.target.checked;
                        setChecklist(newC);
                      }}
                      disabled={isBlocked || !isActive || !isLearner}
                      className="mt-1 h-4 w-4 rounded border-gray-300 text-green focus:ring-green"
                    />
                    <span className="text-sm text-ink">{checkItem}</span>
                  </label>
                ))}
              </div>
              {isLearner && isActive && !isBlocked && (
                <Button onClick={handleSaveProgress} variant="secondary" size="sm">Save checklist</Button>
              )}
            </section>

            {item.quiz && (
              <section className="space-y-4 bg-paper p-5 rounded-lg border border-border">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Knowledge Check</h3>
                  {quiz_passed && (
                    <Badge variant="success">Quiz Passed</Badge>
                  )}
                </div>
                <p className="font-medium text-sm">{item.quiz.question}</p>
                <div className="space-y-2">
                  {item.quiz.options?.map((opt, idx) => (
                    <label key={idx} className="flex items-center space-x-3 p-2 rounded hover:bg-white cursor-pointer">
                      <input 
                        type={multiple ? 'checkbox' : 'radio'}
                        name={`quiz-${item.requirement_id}`}
                        value={idx}
                        checked={multiple ? selectedAnswers.includes(idx) : selectedAnswer === idx}
                        onChange={() => multiple ? setSelectedAnswers(values => values.includes(idx) ? values.filter(value => value !== idx) : [...values, idx]) : setSelectedAnswer(idx)}
                        disabled={isBlocked || !isActive || !isLearner}
                        className="h-4 w-4 text-green focus:ring-green"
                      />
                      <span className="text-sm text-ink">{opt}</span>
                    </label>
                  ))}
                </div>
                
                {isLearner && isActive && !isBlocked && (
                  <Button onClick={handleCheckAnswer} size="sm" className="mt-2 bg-green text-white hover:bg-green/90">
                    Check answer
                  </Button>
                )}

                {quiz_attempts && quiz_attempts.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <h4 className="text-sm font-medium mb-2">Past attempts:</h4>
                    <div className="space-y-1">
                      {quiz_attempts.map((att, i) => (
                        <div key={i} className="text-xs flex items-center gap-2">
                          {att.passed ? <CheckCircle2 className="h-3 w-3 text-green" /> : <XCircle className="h-3 w-3 text-destructive" />}
                          <span className="text-muted">{formatDateTime(att.created_at)}</span>
                          {!att.passed && att.feedback && <span className="text-muted">- {att.feedback}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}
          </div>

          {/* Column 2: Practical Task */}
          <div className="space-y-6">
            <section className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-green" /> Practical Assignment
              </h3>
              
              <div className="bg-paper p-4 rounded-md border border-border space-y-4">
                <div>
                  <h4 className="font-medium text-sm">Activity Instructions</h4>
                  <p className="text-sm text-muted mt-1 whitespace-pre-wrap">{item.practical_activity}</p>
                </div>
                {item.scenario && (
                  <div>
                    <h4 className="font-medium text-sm">Scenario Prompt</h4>
                    <p className="text-sm text-muted mt-1 whitespace-pre-wrap">{item.scenario.prompt}</p>
                  </div>
                )}
              </div>

              {item.rubric && item.rubric.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Assessment Rubric</h4>
                  <div className="border border-border rounded-md overflow-hidden bg-white">
                    <table className="w-full text-xs">
                      <thead className="bg-paper border-b border-border text-muted">
                        <tr>
                          <th className="px-3 py-2 text-left">Criterion</th>
                          <th className="px-3 py-2 text-right">Max Points</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {item.rubric.map((r, i) => (
                          <tr key={i}>
                            <td className="px-3 py-2">{r.criterion}</td>
                            <td className="px-3 py-2 text-right font-medium">{r.max_points}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>

            {/* Submission Section */}
            {isLearner && isActive && !isBlocked && !practical_passed && (!latest_submission || latest_submission.status !== 'pending') && (
              <section className="space-y-4 p-5 rounded-lg border border-border bg-white shadow-sm">
                <h4 className="font-medium text-sm">Submit Assignment</h4>
                <div className="space-y-3">
                  <div>
                    <Label className="text-xs">Scenario Response</Label>
                    <Textarea 
                      value={scenarioResp} 
                      onChange={(e) => setScenarioResp(e.target.value)} 
                      placeholder="Write your response to the scenario prompt..."
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Practical Work Output</Label>
                    <Textarea 
                      value={practicalResp} 
                      onChange={(e) => setPracticalResp(e.target.value)} 
                      placeholder="Paste your practical activity solution here..."
                      rows={4}
                    />
                  </div>
                  <Button onClick={handleSubmitPractical} className="w-full bg-green text-white hover:bg-green/90">
                    Submit for assessment
                  </Button>
                </div>
              </section>
            )}

            {/* Assessor Grading Form */}
            {isReviewerOrManager && latest_submission && latest_submission.status === 'pending' && (
              <section className="space-y-4 p-5 rounded-lg border border-amber/30 bg-amber/5">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium text-amber-900">Grade Pending Submission</h4>
                  <Badge variant="warning">Awaiting Assessment</Badge>
                </div>
                
                <div className="space-y-2 text-sm">
                  <p className="font-medium text-xs text-muted uppercase">Learner Scenario Response:</p>
                  <p className="bg-white p-3 rounded border border-border text-ink whitespace-pre-wrap">{latest_submission.scenario_response}</p>
                  
                  <p className="font-medium text-xs text-muted uppercase mt-2">Learner Practical Output:</p>
                  <p className="bg-white p-3 rounded border border-border text-ink whitespace-pre-wrap">{latest_submission.practical_response}</p>
                </div>

                <div className="space-y-3 pt-3 border-t border-amber/20">
                  <p className="text-xs font-semibold uppercase text-muted">Rubric Scores</p>
                  {item.rubric?.map((r, i) => (
                    <div key={i} className="flex justify-between items-center gap-4">
                      <Label className="text-xs flex-1">{r.criterion} (max {r.max_points})</Label>
                      <Input 
                        type="number" 
                        min={0} 
                        max={r.max_points} 
                        className="w-20 text-right h-8"
                        onChange={(e) => setScores(prev => ({ ...prev, [`score_${i}`]: parseInt(e.target.value) || 0 }))}
                      />
                    </div>
                  ))}
                  <div>
                    <Label className="text-xs">Assessor Feedback</Label>
                    <Textarea 
                      value={feedback} 
                      onChange={(e) => setFeedback(e.target.value)} 
                      placeholder="Provide constructive feedback for the learner..."
                      rows={3}
                    />
                  </div>
                  <Button onClick={() => handleGradeSubmission(latest_submission._id)} className="w-full bg-green text-white hover:bg-green/90">
                    Grade submission
                  </Button>
                </div>
              </section>
            )}

            {/* Submissions History */}
            {row.submissions && row.submissions.length > 0 && (
              <section className="space-y-4 pt-4 border-t border-border">
                <h4 className="font-medium text-sm">Submission History</h4>
                <div className="space-y-3">
                  {row.submissions.map((sub) => (
                    <div key={sub._id} className="p-4 rounded-md border border-border bg-paper space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span className="font-medium text-muted">{formatDateTime(sub.created_at)}</span>
                        <Badge variant={sub.status === 'pending' ? 'warning' : sub.passed ? 'success' : 'destructive'}>
                          {sub.status === 'pending' ? 'Pending' : `${sub.percent}% (${sub.passed ? 'Passed' : 'Failed'})`}
                        </Badge>
                      </div>
                      {sub.feedback && (
                        <div className="text-xs text-muted pt-2 border-t border-border">
                          <span className="font-semibold text-ink">Feedback: </span>
                          <span className="italic">{sub.feedback}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default LearnPage;
