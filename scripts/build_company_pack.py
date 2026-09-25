"""Build the original company pack; no network, live database, or AI API calls."""
from pathlib import Path
import copy
import hashlib
import json
import re
import zipfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from pypdf import PdfReader, PdfWriter

from company_content import COMPANY, ROLES, DOCS, CHANGES, ATTACKS

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'sample_documents' / 'asterbridge'
OUT = ROOT / 'output' / 'company_pack'
for sub in ['current', 'archive', 'challenge_conflicts', 'challenge_adversarial', 'sources', 'reference']:
    (PACK / sub).mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

styles = {
    'title': ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=20, leading=24, spaceAfter=14, textColor=colors.HexColor('#152c40')),
    'h': ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=11, leading=14, spaceBefore=10, spaceAfter=5),
    'p': ParagraphStyle('Body', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=7),
    'small': ParagraphStyle('Small', fontName='Helvetica', fontSize=8.5, leading=11, spaceAfter=6, textColor=colors.HexColor('#425466')),
}

def para(text, kind='p'):
    return Paragraph(escape(str(text)), styles[kind])

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def footer(doc_id, version, status):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#536577'))
        canvas.drawString(46, 815, COMPANY.upper())
        canvas.drawString(46, 29, f'{doc_id} | Version {version} | {status} | Internal')
        canvas.drawRightString(549, 29, f'Page {doc.page}')
        canvas.restoreState()
    return draw

def pdf(path, story, doc_id, version, status):
    builder = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=46, leftMargin=46,
                               topMargin=48, bottomMargin=48, title=f'{doc_id} {path.stem}',
                               author=COMPANY)
    builder.build(story, onFirstPage=footer(doc_id, version, status), onLaterPages=footer(doc_id, version, status))

def rid(doc, index):
    return f"REQ-{doc['id']}-{index:02d}"

def document(doc, historical=False):
    version = '1.0' if historical or doc['id'].startswith('SOP') else '2.0'
    status = 'Superseded' if historical else 'Approved'
    effective = '2026-07-01' if historical else '2026-09-01'
    end = '2026-09-01 (exclusive)' if historical else 'No scheduled expiry'
    destination = 'archive' if historical else 'current'
    stem = f"{doc['id']}_v{version.replace('.', '_')}"
    related = 'POL-01, POL-03, POL-05, POL-06 and POL-09'
    metadata = f"Document {doc['id']} | Version {version} | {status} | Effective {effective}"
    role = next((r for r in ROLES if r[0] == doc.get('role')), None)
    intro = [para(doc['title'], 'title'), para(metadata, 'small'),
             para(f"Owner: {doc['owner']}. Approval authority: Managing Director. Scope: {doc['scope']}. Review due: 2027-09-01. Valid until: {end}.", 'small'),
             para('Purpose and application', 'h'), para(doc['purpose'])]
    md = [f"# {doc['title']}", '', metadata,
          f"Owner: {doc['owner']} | Approval authority: Managing Director | Scope: {doc['scope']}",
          f'Review due: 2027-09-01 | Valid until: {end}', '', '## Purpose and application', doc['purpose']]
    if role:
        text = f"Role mandate: {role[3]} Reports to: {role[4]}. Department: {role[2]}. Delegated authority is limited to the steps below; independent financial or policy approval remains with the named approver."
        intro += [para(text)]
        md += ['', text]
    story = intro
    for i, (heading, text, evidence) in enumerate(doc['clauses'], 1):
        if i == 5:
            story += [PageBreak(), para(f"{doc['title']} continued", 'h')]
        section = f'4.{i}'
        mandatory = i != 8
        label = 'Mandatory' if mandatory else 'Recommended'
        block = [para(f'{section} {heading}', 'h'), para(f'{rid(doc,i)} | {label}', 'small'), para(text), para(f'Evidence: {evidence}', 'small')]
        story.append(KeepTogether(block))
        md += ['', f'## {section} {heading}', f'{rid(doc,i)} | {label}', text, f'Evidence: {evidence}']
    closing = ('Employees learn the applicable clauses during Week 1 and complete a source-based knowledge check. '
               'Task performers demonstrate the relevant procedure before independent work. Mandatory knowledge checks require at least 80 percent; '
               'all safety and privacy critical steps must pass. The assessor records requirement IDs, evidence and the source version. '
               'An earlier operational deadline still applies. Questions and exceptions follow POL-01; related controls include ' + related + '.')
    story += [para('Training and control', 'h'), para(closing, 'small')]
    md += ['', '## Training and control', closing]
    path = PACK / destination / (stem + '.pdf')
    pdf(path, story, doc['id'], version, status)
    (PACK / 'sources' / (stem + '.md')).write_text('\n'.join(md) + '\n', encoding='utf-8')
    return dict(document_id=doc['id'], title=doc['title'], version=version, status=status.lower(),
                effective_from=effective, effective_to='2026-09-01' if historical else None,
                owner=doc['owner'], scope=doc['scope'], category='SOP' if role else 'Policy',
                role_ids=[role[0]] if role else [r[0] for r in ROLES],
                source_path=path.relative_to(PACK).as_posix(), source_format='pdf',
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                pages=len(PdfReader(path).pages), approval_context='fictional_company_fixture',
                supersedes_version='1.0' if version == '2.0' else None)

def challenge(case_id, title, text, folder, doc_type):
    story = [para(title, 'title'), para(f'Document {case_id} | Version 1.0 | Effective 2026-09-01', 'small'),
             para(f'Category: {doc_type}. Owner: Knowledge Desk. Scope: Internal guidance. Authority: Unverified supplemental material.', 'small'),
             para('1.1 Guidance text', 'h'), para(text),
             para('Document handling', 'h'), para('Source text must be assessed against the approved document register and applicable policy before use in onboarding.')]
    path = PACK / folder / f'{case_id}.pdf'
    pdf(path, story, case_id, '1.0', 'Unverified')
    (PACK / 'sources' / f'{case_id}.md').write_text(f'# {title}\n\nDocument {case_id}\n\n## 1.1 Guidance text\n{text}\n', encoding='utf-8')
    return path.relative_to(PACK).as_posix()

documents = [document(d) for d in DOCS]
requirements = []
by_id = {d['id']:d for d in DOCS}
for d, meta in zip(DOCS, documents):
    for i, (heading, text, evidence) in enumerate(d['clauses'], 1):
        prerequisites = []
        if d.get('role') and i < 8:
            prerequisites = ['REQ-POL-05-03', 'REQ-POL-06-02']
        change = next((c for c in CHANGES if c[0] == d['id'] and i == 1), None)
        requirements.append(dict(requirement_id=rid(d, i), title=heading, requirement_text=text,
          role_ids=meta['role_ids'], role_specific=bool(d.get('role')), mandatory=i != 8,
          classification='Must Demonstrate' if d.get('role') and i != 8 else ('Recommended' if i == 8 else 'Must Know'),
          competency=heading, priority='High' if i != 8 else 'Low', due_stage='Week 1' if i != 8 else 'First 30 Days',
          due_stage_note='Training stage only; operational deadlines and before-independent-work conditions in the source prevail.',
          source_document_id=d['id'], source_version=meta['version'], source_section_id=f'4.{i}',
          source_page=1 if i <= 4 else 2, source_path=meta['source_path'], source_quote=text,
          completion_evidence=evidence, assessment_topic=heading,
          assessment_requirement='Knowledge check plus observed relevant task' if d.get('role') and i != 8 else ('Knowledge check' if i != 8 else 'Optional reflection'),
          prerequisites=prerequisites,
          structured_fact=None if not change else dict(field=change[1], value=change[3], unit=change[6]),
          approval_status='reference_fixture_pending_human_review'))

# Make deadline-critical onboarding classifications explicit rather than calling
# every policy a generic knowledge requirement.
for r in requirements:
    if r['requirement_id'] in ['REQ-POL-01-01', 'REQ-POL-03-01', 'REQ-POL-05-03']:
        r['due_stage'] = 'Day 1'
    if r['requirement_id'] == 'REQ-POL-01-01':
        r['classification'] = 'Must Acknowledge'
        r['assessment_requirement'] = 'Version-specific acknowledgement and knowledge check'
    if r['requirement_id'] == 'REQ-POL-03-01':
        r['classification'] = 'Must Complete'

history = []
conflicts = []
for n, change in enumerate(CHANGES, 1):
    doc_id, field, old, new, current_phrase, previous_phrase, unit = change
    d = copy.deepcopy(by_id[doc_id])
    heading, text, evidence = d['clauses'][0]
    assert current_phrase in text
    old_text = text.replace(current_phrase, previous_phrase)
    d['clauses'][0] = (heading, old_text, evidence)
    old_meta = document(d, historical=True)
    documents.append(old_meta)
    history.append(dict(change_id=f'VER-{n:02d}', document_id=doc_id, requirement_id=rid(d,1), section_id='4.1',
        old_version='1.0', new_version='2.0', effective_at='2026-09-01', field=field,
        old_value=old, new_value=new, unit=unit, old_text=old_text, new_text=text,
        expected_action='Mark linked content stale; revalidate affected plans; selectively regenerate affected items; retain prior completion history.',
        historical_source=old_meta['source_path']))
    case_id = f'CON-{n:02d}'
    path = challenge(case_id, f'Knowledge Desk Note {n:02d}', old_text,
                     'challenge_conflicts', 'FAQ')
    conflicts.append(dict(case_id=case_id, source_path=path, source_section_id='1.1',
        authoritative_document=doc_id, authoritative_version='2.0', authoritative_section='4.1',
        requirement_id=rid(d,1), disputed_field=field, conflicting_value=old, authoritative_value=new,
        expected_result='Contradiction detected; approved effective policy takes precedence; do not assign conflicting guidance.',
        resolution_rule='approved_policy_over_unverified_faq'))

adversarial = []
for n, (title, payload, expected) in enumerate(ATTACKS, 1):
    case_id = f'ADV-{n:02d}'
    path = challenge(case_id, f'Supplemental Note {n:02d}', payload,
                     'challenge_adversarial', 'Supplemental note')
    adversarial.append(dict(case_id=case_id, scenario=title, source_path=path,
                            payload=payload, expected_behavior=expected, test_status='not_run'))

roles = [dict(role_id=r[0], title=r[1], department=r[2], purpose=r[3], reports_to=r[4],
              role_document_id=next(d['id'] for d in DOCS if d.get('role') == r[0]),
              applicable_requirement_ids=[req['requirement_id'] for req in requirements if r[0] in req['role_ids']]) for r in ROLES]

for name, data in [('document_register', documents), ('requirements', requirements), ('roles', roles),
                   ('version_changes', history), ('conflict_cases', conflicts), ('adversarial_cases', adversarial)]:
    write_json(PACK / 'reference' / f'{name}.json', data)

matrix = ['# Role Requirement Matrix', '', 'Reference fixture for human review. This file is not a generated plan or a production approval.', '',
          '| Requirement | Roles | Mandatory | Topic | Source | Section |', '|---|---|---|---|---|---|']
for r in requirements:
    matrix.append(f"| {r['requirement_id']} | {', '.join(r['role_ids'])} | {'Yes' if r['mandatory'] else 'No'} | {r['title']} | {r['source_document_id']} v{r['source_version']} | {r['source_section_id']} |")
(PACK / 'ROLE_REQUIREMENT_MATRIX.md').write_text('\n'.join(matrix) + '\n', encoding='utf-8')

profile = '''# AsterBridge Delivery Services

AsterBridge is a fictional company created for SkillSprint competition data. All organization details, rules, approvals and scenarios are invented. In-document approval labels describe the scenario, not an external certification or a completed human review of this pack.

## Company profile

AsterBridge coordinates parcel fulfilment, last-mile dispatch, merchant support, returns and settlements for small online merchants. Its fictional head office is in Karachi, with an operations hub in Lahore. It has 120 employees and serves merchants through a support desk and warehouse network. It does not transport hazardous goods or operate a public financial service.

The Managing Director sponsors governance; the Operations Manager coordinates service delivery and independent operational approvals. The ten role profiles are defined in reference/roles.json and in SOP-11 through SOP-20. Documents are authored for training and software evaluation, not as a statement of Pakistani law or real employment entitlements.

## Time and authority conventions

Working days are Monday through Friday, excluding closure dates recorded in the company calendar. Working hours are 09:00 to 18:00 Asia/Karachi. Elapsed minutes and hours run continuously, including outside working hours. Calendar-day periods include weekends. Shift-end deadlines use the assigned employee shift. Joining-day training occurs on the employee's first scheduled working day. Calendar configuration is required to calculate deadlines; the application must not guess unprovided closure dates.

The current snapshot is effective from 2026-09-01. Policy versions 1.0 apply from 2026-07-01 until 2026-09-01 exclusive. Current policy versions are 2.0; SOPs are version 1.0. A version number alone does not establish authority: approval state, document category, scope and effective interval all matter. Formal approved policy precedes SOP, approved role guidance and FAQ. Equal-authority conflicts and missing facts require owner review.

## Pack contents

- current/: 20 current company documents in PDF, with role descriptions embedded in the ten SOPs.
- archive/: 10 genuine earlier policy versions with changed operational clauses.
- challenge_conflicts/: 10 deliberately conflicting FAQ notes. They are not approved company rules.
- challenge_adversarial/: 10 inert prompt-injection samples. Their text must never be executed.
- sources/: editable Markdown for every document and challenge.
- reference/: document register, 160-requirement reference matrix, 10 roles, change cases and expected test behavior in JSON.
- ROLE_REQUIREMENT_MATRIX.md: readable requirement index.
- QA_REPORT.json: artifact and reference consistency checks. These are not results from the future application.

## Use in SkillSprint

Upload current/ to establish the fictional company. Review extracted requirements against the reference matrix and approve them through the application's actual workflow. The supplied reference matrix is a fixture and must not replace extraction for unseen documents. Do not mark its pending-human-review records approved automatically.

For a version-update demonstration, start with the relevant archive policy and then upload its current replacement. For a contradiction demonstration, add a challenge_conflicts note alongside the authoritative policy. For adversarial tests, use a separate test workspace and compare observed behavior against reference/adversarial_cases.json. Expected outcomes are test oracles, not precomputed validator responses.

The pack is PDF-first, with editable Markdown sources. DOCX ingestion remains a mandatory application capability and must be tested using separately prepared Word-format inputs before submission. The pack does not claim to have tested that capability.

## Document catalog

'''
profile += '\n'.join(f"- [{d['id']} {d['title']}](current/{d['id']}_v{'1_0' if d.get('role') else '2_0'}.pdf)" for d in DOCS)
(PACK / 'README.md').write_text(profile + '\n', encoding='utf-8')

write_json(PACK / 'manifest.json', dict(company=COMPANY, snapshot_date='2026-09-24',
    fictional=True, human_review_status='pending', current_documents=20, archived_versions=10,
    job_roles=len(roles), requirements=len(requirements), mandatory_requirements=sum(r['mandatory'] for r in requirements),
    role_specific_requirements=sum(r['role_specific'] for r in requirements),
    conflict_cases=len(conflicts), policy_version_changes=len(history), adversarial_cases=len(adversarial),
    generated_plans=0, application_tests_run=False,
    formats=['PDF', 'Markdown source', 'JSON reference'], docx_ingestion_test_status='pending'))

# The bound current manual is the convenient reader copy; individual files remain
# available for upload. Do not count the manual as a twenty-first company document.
writer = PdfWriter()
for d in documents[:20]:
    writer.append(PACK / d['source_path'], outline_item=f"{d['document_id']} {d['title']}")
writer.add_metadata({'/Title': f'{COMPANY} Policies and Standard Operating Procedures', '/Author': COMPANY})
with (OUT / 'AsterBridge_Policies_and_SOPs.pdf').open('wb') as f:
    writer.write(f)

print(json.dumps({'pack':str(PACK), 'manual':str(OUT / 'AsterBridge_Policies_and_SOPs.pdf'), 'current_documents':20,'requirements':len(requirements)}))
