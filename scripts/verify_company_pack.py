"""Check dataset artifacts and render review sheets; not application validation."""
from pathlib import Path
import hashlib
import json
import zipfile
from PIL import Image, ImageDraw
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'sample_documents' / 'asterbridge'
QA = ROOT / 'tmp' / 'company_pack_qa'
QA.mkdir(parents=True, exist_ok=True)

def read(name):
    return json.loads((PACK/'reference'/f'{name}.json').read_text(encoding='utf-8'))

docs=read('document_register'); reqs=read('requirements'); roles=read('roles')
current={(d['document_id'],d['version']):d for d in docs if d['status']=='approved'}
assert len(current)==20 and len(roles)==10 and len(reqs)==160
assert len({r['requirement_id'] for r in reqs})==160
assert sum(r['mandatory'] for r in reqs)==140
assert sum(r['role_specific'] for r in reqs)==80
reqids={r['requirement_id'] for r in reqs}
for d in docs:
    path=PACK/d['source_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
    assert len(PdfReader(path).pages)==2, (path,'Expected 2 pages')
for r in reqs:
    assert (r['source_document_id'],r['source_version']) in current
    p=PdfReader(PACK/r['source_path']).pages[r['source_page']-1]
    text=' '.join(p.extract_text().split())
    assert ' '.join(r['source_quote'].split()) in text, r['requirement_id']
    assert r['source_section_id'] in text and r['requirement_id'] in text
    assert set(r['prerequisites'])<=reqids
    assert r['requirement_id'] not in r['prerequisites']
for role in roles:
    assert len(role['applicable_requirement_ids'])==88
for name in ['version_changes','conflict_cases','adversarial_cases']:
    assert len(read(name))==10
for c in read('version_changes'):
    text=' '.join(PdfReader(PACK/c['historical_source']).pages[0].extract_text().split())
    assert ' '.join(c['old_text'].split()) in text
    assert c['old_value']!=c['new_value']

pages=[]
for path in sorted(PACK.rglob('*.pdf')):
    pdf=pdfium.PdfDocument(str(path))
    for i in range(len(pdf)):
        img=pdf[i].render(scale=1.3).to_pil().convert('RGB')
        out=QA/f'{path.stem}_p{i+1}.png'
        img.save(out)
        pages.append((f'{path.parent.name}/{path.stem} / {i+1}',out))
    pdf.close()
# Four pages per sheet for navigation; individual full-size renders are retained.
for start in range(0,len(pages),4):
    batch=pages[start:start+4]
    sheet=Image.new('RGB',(1600,2300),'#dce3e8'); draw=ImageDraw.Draw(sheet)
    for i,(label,path) in enumerate(batch):
        img=Image.open(path); img.thumbnail((780,1100))
        x=(i%2)*800+10; y=(i//2)*1150+35
        sheet.paste(img,(x,y)); draw.text((x,y-24),label,fill='black')
    sheet.save(QA/f'sheet_{start//4+1:02d}.png')

report=dict(artifact_checks='passed', checks=['20 current documents','10 historical versions','160 unique requirements',
    '140 mandatory requirements','80 role-specific requirements','10 roles with 88 applicable requirements each',
    '10 actual version changes','10 conflict cases','10 adversarial cases','all PDF source quotes and pages match',
    'all document hashes match','all prerequisite IDs resolve'],
    rendered_pages=len(pages), visual_review='pending', application_tests='not_run', human_content_review='pending')
(PACK/'QA_REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
