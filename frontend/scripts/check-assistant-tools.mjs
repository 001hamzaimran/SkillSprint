import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/lib/assistantTools.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { runAssistantTool, readDocument, confirmActivation } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const document = { _id: 'd1', document_id: 'SEC-01', title: 'Security Policy', version: '1', effective_date: '2025-01-01', category: 'Policy', status: 'draft', suspicious: false };
let posts = 0, reads = 0;
const client = {
  get: async path => {
    reads++;
    if (path === 'documents') return { documents: [document] };
    if (path === 'plans') return { plans: [{ _id: 'p1', content: { title: 'My plan' }, status: 'Published' }] };
    return { document: { ...document }, sections: [{ section_id: 's1', heading: 'Lock screens', text: 'Employees must lock their screens.' }] };
  },
  post: async path => { assert.equal(path, 'documents/d1/activate'); posts++; },
};
assert.equal((await runAssistantTool(client, 'What is in the knowledge library?', 'admin')).cards[0].title, document.title);
assert.equal(posts, 0);
const excerpt = await runAssistantTool(client, 'Read Security Policy', 'admin');
assert.equal(excerpt.cards[1].quote, 'Employees must lock their screens.');
assert.equal(excerpt.cards[1].route, '/documents/d1#s1');
assert.equal((await runAssistantTool(client, 'Read it', 'reviewer', [document])).cards[1].quote, excerpt.cards[1].quote);
assert.equal((await runAssistantTool(client, 'Activate Security Policy', 'reviewer')).cards[0].actions[0].kind, 'activate');
assert.equal(posts, 0, 'Reading or proposing activation must never mutate');
assert.equal((await runAssistantTool(client, 'Show my plans', 'employee')).cards[0].title, 'My plan');
const before = reads;
assert.equal((await runAssistantTool(client, 'What is in the knowledge library?', 'employee')).cards.length, 0);
assert.equal(reads, before, 'Forbidden tools should not even request library data');
await assert.rejects(() => readDocument(client, 'manager', 'd1'));
await assert.rejects(() => confirmActivation(client, 'training_manager', document));
assert.equal((await runAssistantTool(client, 'Activate Security Policy', 'training_manager')).cards.length, 0);
assert.equal((await runAssistantTool(client, 'Read nonexistent document', 'admin')).cards.length, 0);
assert.equal((await runAssistantTool(client, 'Activate nonexistent document', 'admin')).cards.length, 0);
await assert.rejects(() => confirmActivation(client, 'admin', { ...document, version: 'old' }));
assert.equal(posts, 0);
await confirmActivation(client, 'reviewer', document);
assert.equal(posts, 1);
document.suspicious = true;
const quarantined = await readDocument(client, 'admin', 'd1');
assert(quarantined.answer.includes('quarantined'));
assert(!quarantined.cards.some(c => c.quote));
await assert.rejects(() => confirmActivation(client, 'admin', document));
assert.equal(posts, 1);
assert.equal(await runAssistantTool(client, 'What is in the knowledge library?', 'guest'), null);
assert.equal(await runAssistantTool(client, 'How do I upload documents?', 'admin'), null);
console.log('Live assistant tools passed: reads, excerpts, follow-ups, safe proposals, confirmation, stale target rejection, quarantine and role restrictions.');
