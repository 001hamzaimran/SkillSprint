import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import { useForm, useFieldArray } from 'react-hook-form';
import { usePlanStore } from '@/stores/planStore';
import { PageHeader } from '@/components/shared/PageHeader';
import { Spinner } from '@/components/shared/Spinner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { toast } from 'sonner';
import { ArrowLeft, Plus, Trash2, ArrowRight } from 'lucide-react';
import { STAGES } from '@/types';

export function EditItemPage() {
  const { planId, reqId } = useParams<{ planId: string, reqId: string }>();
  const navigate = useNavigate();
  const { fetchEditItem, editItem, isLoading } = usePlanStore();
  const [sourceQuote, setSourceQuote] = useState('');

  const { register, handleSubmit, control, reset } = useForm({
    defaultValues: {
      module_title: '',
      learning_objective: '',
      stage: 'Day 1',
      estimated_minutes: 30,
      lesson: '',
      checklist: '',
      practical_activity: '',
      scenario_prompt: '',
      scenario_expected: '',
      question: '',
      options: '',
      correct_index: 0,
      explanation: '',
      rubric: [{ criterion: '', max_points: 10 }],
      reason: ''
    }
  });

  const { fields: rubricFields, append: appendRubric, remove: removeRubric } = useFieldArray({
    control,
    name: "rubric"
  });

  useEffect(() => {
    if (planId && reqId) {
      fetchEditItem(planId, reqId).then((data: any) => {
        if (data) {
          const item = data.item || data;
          setSourceQuote(item.source_quote || '');
          reset({
            module_title: item.module_title || '',
            learning_objective: item.learning_objective || '',
            stage: item.stage || 'Day 1',
            estimated_minutes: item.estimated_minutes || 30,
            lesson: item.lesson || '',
            checklist: (item.checklist || []).join('\n'),
            practical_activity: item.practical_activity || '',
            scenario_prompt: item.scenario?.prompt || item.scenario_prompt || '',
            scenario_expected: item.scenario?.expected_response || item.scenario_expected || '',
            question: item.quiz?.question || item.question || '',
            options: (item.quiz?.options || item.options || []).join('\n'),
            correct_index: item.quiz?.correct_index ?? item.correct_index ?? 0,
            explanation: item.quiz?.explanation || item.explanation || '',
            rubric: item.rubric && item.rubric.length > 0 ? item.rubric : [{ criterion: '', max_points: 10 }],
            reason: ''
          });
        }
      });
    }
  }, [planId, reqId, fetchEditItem, reset]);

  const onSubmit = async (formData: any) => {
    try {
      const payload = {
        module_title: formData.module_title,
        learning_objective: formData.learning_objective,
        stage: formData.stage,
        estimated_minutes: Number(formData.estimated_minutes),
        lesson: formData.lesson,
        checklist: formData.checklist.split('\n').map((l: string) => l.trim()).filter(Boolean),
        practical_activity: formData.practical_activity,
        scenario_prompt: formData.scenario_prompt,
        scenario_expected: formData.scenario_expected,
        question: formData.question,
        options: formData.options.split('\n').map((l: string) => l.trim()).filter(Boolean),
        correct_index: Number(formData.correct_index),
        explanation: formData.explanation,
        rubric: formData.rubric.map((r: any) => ({ criterion: r.criterion, max_points: Number(r.max_points) })),
        reason: formData.reason,
      };

      const newPlanId = await editItem(planId!, reqId!, payload);
      toast.success('Module draft saved and revalidated');
      navigate(`/plans/${newPlanId}`);
    } catch {
      toast.error('Failed to update module');
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="space-y-4">
        <Link to={`/plans/${planId}`} className="inline-flex items-center text-sm font-medium text-muted hover:text-ink transition-colors">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to plan
        </Link>
        <PageHeader 
          eyebrow="A REVIEWABLE REVISION"
          title="Edit learning module"
          subtitle={`Editing requirement: ${reqId}`}
        />
      </div>

      {sourceQuote && (
        <div className="p-4 rounded-lg bg-paper border border-border text-sm italic text-muted">
          <span className="font-semibold text-ink not-italic">Source passage: </span>
          "{sourceQuote}"
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Module Title</Label>
                <Input {...register("module_title", { required: true })} />
              </div>
              <div className="space-y-2">
                <Label>Stage</Label>
                <Select {...register("stage", { required: true })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Learning Objective</Label>
                <Input {...register("learning_objective", { required: true })} />
              </div>
              <div className="space-y-2">
                <Label>Estimated Minutes</Label>
                <Input type="number" {...register("estimated_minutes", { required: true })} />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Lesson Content</Label>
              <Textarea {...register("lesson", { required: true })} rows={6} />
            </div>

            <div className="space-y-2">
              <Label>Checklist Items (one per line)</Label>
              <Textarea {...register("checklist")} rows={4} placeholder="Read policy&#10;Complete orientation&#10;Confirm understanding" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Practical Assignment & Scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Practical Activity Instructions</Label>
              <Textarea {...register("practical_activity", { required: true })} rows={3} />
            </div>
            <div className="space-y-2">
              <Label>Scenario Prompt</Label>
              <Textarea {...register("scenario_prompt", { required: true })} rows={3} />
            </div>
            <div className="space-y-2">
              <Label>Expected Scenario Response</Label>
              <Textarea {...register("scenario_expected", { required: true })} rows={3} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Knowledge Check Quiz</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Quiz Question</Label>
              <Input {...register("question", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label>Answer Options (one per line)</Label>
              <Textarea {...register("options", { required: true })} rows={4} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Correct Option Index (0-based)</Label>
                <Input type="number" min={0} {...register("correct_index", { required: true })} />
              </div>
              <div className="space-y-2">
                <Label>Explanation</Label>
                <Input {...register("explanation", { required: true })} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Assessment Rubric</CardTitle>
            <Button type="button" variant="secondary" size="sm" onClick={() => appendRubric({ criterion: '', max_points: 10 })}>
              <Plus className="w-4 h-4 mr-1" /> Add Criterion
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {rubricFields.map((field, idx) => (
              <div key={field.id} className="flex gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <Label>Criterion #{idx + 1}</Label>
                  <Input {...register(`rubric.${idx}.criterion`, { required: true })} />
                </div>
                <div className="w-24 space-y-2">
                  <Label>Max Pts</Label>
                  <Input type="number" min={1} {...register(`rubric.${idx}.max_points`, { required: true })} />
                </div>
                {rubricFields.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeRubric(idx)} className="text-red-500 mb-0.5">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit Reason</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label>Reason for edit (required for revalidation audit trail)</Label>
              <Textarea {...register("reason", { required: true })} placeholder="Explain what was edited and why..." rows={3} />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" size="lg" className="w-full bg-green text-white hover:bg-green/90">
              Save new draft and revalidate <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}

export default EditItemPage;
