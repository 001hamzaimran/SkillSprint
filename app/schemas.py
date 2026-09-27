from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, StringConstraints
from typing import Annotated

Stage = Literal["Day 1", "Week 1", "Week 2", "First 30 Days", "First 60 Days", "First 90 Days"]
STAGES = ["Day 1", "Week 1", "Week 2", "First 30 Days", "First 60 Days", "First 90 Days"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedRequirement(StrictModel):
    section_id: str
    title: str
    source_quote: str
    mandatory: bool
    due_stage: Stage
    competency: str
    classification: Literal[
        "Must Know",
        "Must Complete",
        "Must Demonstrate",
        "Must Acknowledge",
        "Recommended",
        "Optional",
        "Not Applicable",
    ] = "Must Know"
    priority: Literal["High", "Medium", "Low"] = "Medium"
    prerequisite_section_ids: list[str] = Field(default_factory=list)
    prerequisite_evidence: str = ""


class Extraction(StrictModel):
    requirements: list[ExtractedRequirement]


class LearningItem(StrictModel):
    requirement_id: str
    role_id: str
    source_document_id: str
    source_section_id: str
    source_quote: str
    mandatory: bool
    stage: Stage
    module_title: str
    learning_objective: str
    practical_activity: str
    estimated_minutes: int = Field(ge=1, le=180)


class OnboardingPlan(StrictModel):
    title: str
    summary: str
    role_id: str
    items: list[LearningItem]


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1200)]


class QuizQuestion(StrictModel):
    question_type: Literal["multiple_choice", "multiple_response", "true_false", "scenario"] = (
        "multiple_choice"
    )
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Beginner"
    question: ShortText
    options: list[ShortText] = Field(min_length=2, max_length=5)
    correct_index: int = Field(ge=0, le=4)
    correct_indices: list[int] = Field(default_factory=list)
    explanation: ShortText
    evidence_quote: str = Field(min_length=3, max_length=6000)

    @model_validator(mode="after")
    def valid_answer(self):
        if self.correct_index >= len(self.options):
            raise ValueError("Correct answer must refer to an existing option.")
        if len({x.strip().casefold() for x in self.options}) != len(self.options):
            raise ValueError("Quiz options must be distinct.")
        if self.question_type == "multiple_response":
            if len(set(self.correct_indices)) < 2 or any(
                i < 0 or i >= len(self.options) for i in self.correct_indices
            ):
                raise ValueError(
                    "Multiple-response questions require at least two valid answer indices."
                )
        elif self.correct_indices:
            raise ValueError("Use correct_index for single-answer questions.")
        if self.question_type == "true_false" and {
            option.casefold() for option in self.options
        } != {"true", "false"}:
            raise ValueError("True/false questions must offer True and False.")
        return self


class Scenario(StrictModel):
    prompt: ShortText
    expected_response: ShortText


class RubricCriterion(StrictModel):
    criterion: ShortText
    max_points: int = Field(ge=1, le=5)
    expected_performance: str = ""


class PolicyRule(StrictModel):
    key: str = Field(min_length=2, max_length=80)
    value: str = Field(min_length=1, max_length=600)
    condition: str = Field(max_length=1200)
    exception: str = Field(max_length=1200)
    answer_fact: str = Field(max_length=1200)
    module_category: str = Field(min_length=2, max_length=120)
    assessment_topic: str = Field(min_length=2, max_length=120)


class FullLearningItem(LearningItem):
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Beginner"
    priority: Literal["High", "Medium", "Low"] = "Medium"
    lesson: str = Field(min_length=30, max_length=5000)
    checklist: list[ShortText] = Field(min_length=2, max_length=6)
    scenario: Scenario
    quiz: QuizQuestion
    rubric: list[RubricCriterion] = Field(min_length=2, max_length=5)
    policy_facts: PolicyRule | None = None

    @model_validator(mode="after")
    def meaningful_lesson(self):
        if len(self.lesson.strip()) < 30:
            raise ValueError("A lesson needs meaningful teaching content.")
        return self


class FullOnboardingPlan(OnboardingPlan):
    items: list[FullLearningItem] = Field(min_length=1, max_length=120)
