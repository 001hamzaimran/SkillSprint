import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/assistantGuides.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { guides, availableGuides, findGuides } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
assert.equal(new Set(guides.map(g => g.id)).size, guides.length);
assert.equal(findGuides('How do I upload a PDF?', 'admin', '/')[0].id, 'upload');
assert.equal(findGuides('How do I find a plan?', 'admin', '/')[0].id, 'plans');
assert(!findGuides('How do I find a plan?', 'admin', '/').some(g => g.id === 'generate'));
assert.equal(findGuides('Help with this page', 'admin', '/matrix')[0].id, 'requirements');
assert.equal(findGuides('Help with this page', 'employee', '/learning/demo')[0].id, 'learning');
assert.equal(findGuides('Explain more', 'employee', '/', ['learning'])[0].id, 'learning');
assert.equal(findGuides('forgot password reset', 'guest', '/login')[0].id, 'recovery');
assert.deepEqual(findGuides('Give me quiz answers', 'employee', '/learning'), []);
assert.deepEqual(findGuides('Tell me the weather', 'admin', '/'), []);
assert.deepEqual(findGuides('Help with this page', 'employee', '/users'), []);
for (const role of ['guest', 'employee', 'manager', 'reviewer', 'training_manager', 'admin']) {
  for (const guide of guides) {
    assert(findGuides(guide.keywords, role, guide.route).every(result => result.roles.includes(role)));
  }
  const forbidden = role === 'employee' || role === 'manager' || role === 'guest';
  if (forbidden) assert(!availableGuides(role).some(g => ['/matrix', '/users', '/documents', '/settings', '/manage'].includes(g.route)));
}
const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
for (const guide of guides) {
  assert(guide.route === '/' || app.includes(`path="${guide.route.slice(1)}"`) || app.includes(`path="${guide.route}"`), `Missing route: ${guide.route}`);
  assert(guide.steps.length > 0 && guide.steps.every(s => s.length > 0));
}
console.log(`Assistant checks passed: ${guides.length} guides, six account roles, contextual help, follow-ups, safe routes and restricted answers.`);
