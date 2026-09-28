/** Local product help: messages never leave the browser and never modify records. */
export type Guide = { id: string; title: string; route: string; roles: string[]; keywords: string; steps: string[] };
const all = ['admin', 'training_manager', 'reviewer', 'manager', 'employee'];
const editors = ['admin', 'training_manager'];
const reviewers = ['admin', 'reviewer'];
const sources = ['admin', 'training_manager', 'reviewer'];
export const guides: Guide[] = [
  { id: 'overview', title: 'Explore SkillSprint', route: '/', roles: all, keywords: 'overview dashboard start website skillsprint help onboarding', steps: ['Overview shows workspace totals and recent plans.', 'The workflow is company knowledge → reviewed requirements → onboarding plans → learning and assessment.', 'Use the sidebar to open features available to your account. On small screens, open the navigation menu beside the logo.'] },
  { id: 'upload', title: 'Upload company knowledge', route: '/documents', roles: editors, keywords: 'upload document pdf docx knowledge library file policy add manual', steps: ['Open Knowledge library and expand Upload new document.', 'Enter the document details, version and effective date. Choose the relevant role if applicable and select a PDF or DOCX.', 'Select Upload Document. Open the uploaded document to inspect its source sections and extraction status.'] },
  { id: 'sources', title: 'Inspect source evidence', route: '/documents', roles: sources, keywords: 'source evidence citation library document policy', steps: ['Open Knowledge library and select a document.', 'Inspect its source sections. Evidence links in requirements and plans lead back to these sources.', 'Extraction is not approval: a reviewer must check requirements before they are treated as approved.'] },
  { id: 'requirements', title: 'Explore role requirements', route: '/matrix', roles: sources, keywords: 'requirement requirements matrix extract mandatory role', steps: ['Open Role requirements and choose the relevant role or filters.', 'Inspect each requirement and its source evidence.', 'A reviewer or administrator must review requirements before they can be used as approved training requirements.'] },
  { id: 'review', title: 'Work through the review queue', route: '/review-queue', roles: reviewers, keywords: 'review approve reject queue approval requirement', steps: ['Open Review queue and select an item needing review.', 'Check the evidence and validation warnings.', 'Use the item’s review controls to record your decision. Opening an item does not approve it.'] },
  { id: 'verification', title: 'Check verification issues', route: '/verification', roles: sources, keywords: 'verification conflict inconsistent contradiction issue', steps: ['Open Verification to inspect flagged issues and their supporting sources.', 'Ask a reviewer or administrator to resolve issues after checking the evidence.'] },
  { id: 'generate', title: 'Generate an onboarding plan', route: '/employees', roles: editors, keywords: 'employee people generate create plan onboarding', steps: ['Open People and check the employee’s role, experience and joining date.', 'Make sure relevant company documents and approved requirements are available.', 'Select Generate plan for that employee and follow the background job. Generated plans still need human review.'] },
  { id: 'manage', title: 'Manage people and roles', route: '/manage', roles: editors, keywords: 'add edit assign employee manager role people profile', steps: ['Open Manage people & roles to create or update profiles and role assignments.', 'Check the role, manager and joining date before saving. These affect plan generation and access.'] },
  { id: 'people', title: 'Find a person', route: '/employees', roles: all, keywords: 'people employee person team', steps: ['Open People to see profiles within your account’s scope.', 'Managers see their assigned team; employees see their own profile. Contact an administrator if an assignment is incorrect.'] },
  { id: 'roles', title: 'Explore job roles', route: '/roles', roles: sources, keywords: 'job department roles', steps: ['Open Job roles to inspect the available roles and departments.', 'An administrator or training manager can manage role definitions and assignments. Job roles are different from application access roles.'] },
  { id: 'plans', title: 'Find an onboarding plan', route: '/plans', roles: all, keywords: 'plan plans onboarding published download export', steps: ['Open Onboarding plans and select a plan you are permitted to view.', 'Inspect its learning stages, modules, evidence and review status.', 'Use the available export controls if you need a copy. Your account role determines which actions are visible.'] },
  { id: 'publish', title: 'Review and publish a plan', route: '/plans', roles: reviewers, keywords: 'publish approve plan review', steps: ['Open Onboarding plans and select the draft plan.', 'Inspect the modules, evidence and validation results. Resolve blocking issues first.', 'In Submit Review, select Approve, enter comments, confirm your decision and submit. Read any validation feedback before proceeding.'] },
  { id: 'learning', title: 'Complete your learning', route: '/learning', roles: all, keywords: 'learn learning sprint quiz checklist practical submit complete progress training lesson', steps: ['Open Learning progress (My Sprint for employees) and choose an available plan.', 'Read the module and evidence, complete the checklist and answer the quiz.', 'Submit practical evidence where requested. Submission may need a reviewer or manager assessment; it is not automatically a pass.', 'If no plan is available, ask your administrator to assign a reviewed, published plan.'] },
  { id: 'assessment', title: 'Assess practical submissions', route: '/assessments', roles: [...reviewers, 'manager'], keywords: 'assessment assessments grade practical submission score rubric', steps: ['Open Assessments and select a submission within your permitted scope.', 'Inspect the evidence and rubric, then record the assessment using the form.'] },
  { id: 'reports', title: 'View reports', route: '/reports', roles: all, keywords: 'report reports completion export analytics', steps: ['Open Reports to inspect learning progress within your account’s scope.', 'Use the available filters and export controls. Employees see their own information; managers see their assigned team.'] },
  { id: 'insights', title: 'Understand progress', route: '/insights', roles: all, keywords: 'insight insights overdue progress analytics', steps: ['Open Progress insights to see the available learning progress indicators.', 'Follow up on incomplete learning using the plan or learning pages. Results depend on your access.'] },
  { id: 'search', title: 'Search the workspace', route: '/search', roles: all, keywords: 'search find locate', steps: ['Open Search and enter a title or keyword.', 'Select a matching result to open it. Results respect your account permissions.'] },
  { id: 'compare', title: 'Compare profiles', route: '/compare', roles: sources, keywords: 'compare profiles experience beginner advanced', steps: ['Open Compare profiles and select the comparison options.', 'Inspect differences in learning content and evidence before changing a plan.'] },
  { id: 'schedule', title: 'Set the onboarding schedule', route: '/settings', roles: ['admin'], keywords: 'schedule deadline days settings', steps: ['Open Onboarding schedule to review the day offsets for learning stages.', 'Update and save the settings carefully. Check affected plans and due dates afterwards.'] },
  { id: 'access', title: 'Manage account access', route: '/users', roles: ['admin'], keywords: 'access user account permission invitation', steps: ['Open Access management to manage accounts and their application roles.', 'Assign only the access each person needs. Employee job roles and application access roles are different.'] },
  { id: 'audit', title: 'Inspect the activity trail', route: '/audit', roles: reviewers, keywords: 'audit activity history trail', steps: ['Open Activity trail to inspect recorded workspace actions.', 'Use the visible filters to locate the event you need.'] },
  { id: 'recovery', title: 'Reset your password', route: '/forgot-password', roles: [...all, 'guest'], keywords: 'password forgot reset recovery login signin sign in', steps: ['Open Forgot password and enter your account email address.', 'Follow the reset link sent to your email. Check spam if it does not arrive.', 'If you still cannot sign in, contact your administrator. Never share your password in chat.'] },
  { id: 'signin', title: 'Sign in to SkillSprint', route: '/login', roles: ['guest'], keywords: 'start help account login website skillsprint onboarding', steps: ['Sign in with the account provided by your administrator.', 'Your account determines which workspace pages you can access. Ask your administrator if you need an account.', 'Once signed in, ask me how to upload documents, find a plan or complete learning.'] },
];

export function availableGuides(role: string) { return guides.filter(g => g.roles.includes(role)); }

export function findGuides(message: string, role: string, path: string, previousIds: string[] = []) {
  const allowed = availableGuides(role);
  const words = new Set(message.toLowerCase().match(/[a-z]+/g) || []);
  if (/\b(passwords?|secret|api key|quiz answers?|correct answers?)\b/i.test(message) && !/\b(reset|forgot|change|recover)\b/i.test(message)) return [];
  if (/\b(this page|here|current page)\b/i.test(message)) {
    return allowed.filter(g => g.route === path || (g.route !== '/' && path.startsWith(g.route + '/'))).slice(0, 2);
  }
  const stopWords = new Set(['a', 'an', 'the', 'to', 'your', 'and', 'in', 'of']);
  const scores = allowed.map(g => ({ g, score:
    g.keywords.split(' ').filter(w => words.has(w)).length +
    (g.title.toLowerCase().match(/[a-z]+/g) || []).filter(w => !stopWords.has(w) && words.has(w)).length * 2,
  })).sort((a, b) => b.score - a.score);
  const threshold = Math.max(1, (scores[0]?.score || 0) * 0.65);
  const matches = scores.filter(x => x.score >= threshold).slice(0, 2).map(x => x.g);
  if (matches.length) return matches;
  if (/\b(next|explain|steps|more|how|that)\b/i.test(message)) return allowed.filter(g => previousIds.includes(g.id)).slice(0, 2);
  return [];
}
