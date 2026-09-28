// Audit literal and templated navigation targets against the actual React routes.
// Dynamic record existence and authorization still need API/browser acceptance tests.
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { matchPath } from 'react-router';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '..');
function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const name = path.join(directory, entry.name);
    return entry.isDirectory() ? files(name) : /\.tsx?$/.test(name) ? [name] : [];
  });
}
function values(node) {
  if (!node) return [];
  if (ts.isJsxExpression(node) || ts.isParenthesizedExpression(node)) return values(node.expression);
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return [node.text];
  if (ts.isTemplateExpression(node)) return [node.head.text + node.templateSpans.map(span => {
    const name = span.expression.getText();
    const sample = name === 'search' ? '?role_id=sample-id' : name === 'hash' ? '#sample-id' : 'sample-id';
    return sample + span.literal.text;
  }).join('')];
  if (ts.isConditionalExpression(node)) return [...values(node.whenTrue), ...values(node.whenFalse)];
  return [];
}
const routes = [];
const links = [];
for (const file of files(path.join(root, 'src'))) {
  const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, file.endsWith('tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  function record(node, kind, expression) {
    for (const target of values(expression)) {
      const line = source.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      links.push({ target, kind, location: `${path.relative(root, file)}:${line}` });
    }
  }
  function visit(node) {
    if (ts.isJsxAttribute(node)) {
      const name = node.name.getText(source);
      if (name === 'path' && file.endsWith('App.tsx')) routes.push(...values(node.initializer));
      if (name === 'to' || name === 'href') record(node, name, node.initializer);
    }
    if (ts.isCallExpression(node) && node.expression.getText(source) === 'navigate') record(node, 'to', node.arguments[0]);
    if (ts.isPropertyAssignment(node) && node.name.getText(source) === 'path' && file.endsWith('Sidebar.tsx')) record(node, 'to', node.initializer);
    ts.forEachChild(node, visit);
  }
  visit(source);
}
const patterns = routes.filter(route => route !== '*').map(route => route.startsWith('/') ? route : `/${route}`);
const rewrites = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8')).rewrites
  .filter(rule => rule.destination.startsWith('https://'));
const failures = [];
let checked = 0;
for (const link of links) {
  if (!link.target.startsWith('/')) continue;
  const pathname = link.target.split(/[?#]/)[0];
  // Download URLs belong to backend rewrites, not the SPA catch-all.
  const matches = link.kind === 'href'
    ? rewrites.some(rule => matchPath(rule.source.replace(':path*', '*'), pathname))
    : patterns.some(pattern => matchPath(pattern, pathname));
  checked++;
  if (!matches) failures.push(`${link.location}: unregistered ${link.kind} target ${link.target}`);
}
assert(patterns.includes('/requirements'), 'Keep the old /requirements bookmark redirect.');
const dashboard = fs.readFileSync(path.join(root, 'src/pages/DashboardPage.tsx'), 'utf8');
assert(!dashboard.includes('"/requirements"'), 'Overview must use the canonical /matrix route.');
assert.equal(failures.length, 0, failures.join('\n'));
console.log(`Navigation audit passed: ${checked} link patterns; ${patterns.length} registered routes. Dynamic IDs, API responses and live permissions are outside this static check.`);
