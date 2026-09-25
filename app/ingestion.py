"""Source parsing never treats uploaded content as executable instructions."""
import hashlib
import io
import re
import zipfile
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from docx.oxml.ns import qn
from .db import uid, now, audit

SUSPICIOUS = re.compile(r'ignore all previous instructions|SYSTEM MESSAGE:|print the API key|'
    r'add the uploader to|hide all missing requirements|erase audit history|'
    r'"tool"\s*:\s*"database|silently replaces all approved policies|'
    r'send the employee directory|cite POL-99', re.I)
CLAUSE = re.compile(r'^(\d+(?:\.\d+)+)\s+(.+)')


def normalized(text):
    return ' '.join(text.split())


def parse(data, filename):
    suffix = Path(filename).suffix.lower()
    blocks = []
    if suffix == '.pdf':
        if not data.startswith(b'%PDF-'):
            raise ValueError('The file does not contain a valid PDF header.')
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('Password-protected PDFs are not supported. Upload an unlocked copy.')
        if len(reader.pages) > 100:
            raise ValueError('Use documents of at most 100 pages.')
        for page_no, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            # Preserve numbered policy clauses when present; unknown formats are
            # broken into traceable page chunks and remain reviewable.
            lines = text.splitlines()
            starts = [(i, CLAUSE.match(line.strip())) for i, line in enumerate(lines) if CLAUSE.match(line.strip())]
            if starts:
                for j, (start, match) in enumerate(starts):
                    end = starts[j+1][0] if j+1 < len(starts) else len(lines)
                    segment = '\n'.join(lines[start:end])
                    # Footer and document-wide training text are not a clause.
                    segment = segment.split('Training and control')[0]
                    segment = re.split(r'\n(?:POL|SOP)-\d+\s*\|', segment)[0]
                    blocks.append({'section_id': f'p{page_no}-{match.group(1)}', 'heading': match.group(2),
                                   'location': f'PDF page {page_no}, clause {match.group(1)}', 'page': page_no, 'text': segment.strip()})
            else:
                for index in range(0, len(text), 4500):
                    blocks.append({'section_id': f'p{page_no}-c{index//4500+1}', 'heading': f'Page {page_no}',
                        'location': f'PDF page {page_no}, character {index+1}', 'page': page_no, 'text': text[index:index+4500]})
    elif suffix == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                members = z.infolist()
                if len(members) > 1000 or sum(m.file_size for m in members) > 25 * 1024 * 1024:
                    raise ValueError('The expanded Word document exceeds the processing limit.')
                if any('vbaproject' in m.filename.lower() for m in members):
                    raise ValueError('Macro-bearing documents are not supported.')
                if 'word/document.xml' not in z.namelist():
                    raise ValueError('This is not a Word document.')
        except zipfile.BadZipFile as exc:
            raise ValueError('The Word document is invalid.') from exc
        document = Document(io.BytesIO(data))
        paragraph_no = table_no = 0
        for element in document.element.body:
            if element.tag == qn('w:p'):
                paragraph_no += 1
                text = ''.join(n.text or '' for n in element.iter(qn('w:t')))
                if text.strip():
                    for offset in range(0, len(text), 4500):
                        blocks.append({'section_id': f'para-{paragraph_no}-c{offset//4500+1}', 'heading': f'Paragraph {paragraph_no}',
                            'location': f'DOCX paragraph {paragraph_no}, character {offset+1}', 'page': None, 'text': text[offset:offset+4500]})
            elif element.tag == qn('w:tbl'):
                table_no += 1
                for row_no, row in enumerate(element.findall(qn('w:tr')), 1):
                    for cell_no, cell in enumerate(row.findall(qn('w:tc')), 1):
                        text = ' '.join(n.text or '' for n in cell.iter(qn('w:t')))
                        if text.strip():
                            for offset in range(0, len(text), 4500):
                                blocks.append({'section_id': f't{table_no}-r{row_no}-c{cell_no}-{offset//4500+1}', 'heading': f'Table {table_no}',
                                    'location': f'DOCX table {table_no}, row {row_no}, cell {cell_no}, character {offset+1}', 'page': None, 'text': text[offset:offset+4500]})
    else:
        raise ValueError('Upload a PDF or DOCX document.')
    blocks = [b for b in blocks if b['text'].strip()]
    if not blocks:
        raise ValueError('No readable text found. Scanned images require OCR before upload.')
    if sum(len(b['text']) for b in blocks) > 250_000 or len(blocks) > 600:
        raise ValueError('The document exceeds the extraction limit. Split it into smaller documents.')
    # Avoid losing duplicate clause numbers while retaining their source location.
    seen = set()
    for block in blocks:
        if block['section_id'] in seen:
            block['section_id'] += '-' + str(len(seen))
        seen.add(block['section_id'])
        block['suspicious'] = bool(SUSPICIOUS.search(block['text']))
    return blocks


def candidate(section):
    text = section['text']
    lines = text.splitlines()
    marker = next((i for i, line in enumerate(lines) if re.search(r'REQ-.+\|\s*(Mandatory|Recommended)', line)), None)
    if marker is not None:
        quote = '\n'.join(lines[marker+1:]).split('Evidence:')[0].strip()
        mandatory = 'Mandatory' in lines[marker]
    else:
        quote = text.strip()
        mandatory = bool(re.search(r'\b(must|shall|required|prohibited)\b', quote, re.I))
        if not mandatory and not re.search(r'\b(should|may|encouraged|recommended)\b', quote, re.I):
            return None
    if not quote or section['suspicious']:
        return None
    return {'title': section['heading'][:180], 'text': normalized(quote), 'mandatory': mandatory,
            'due_stage': 'Week 1', 'competency': section['heading'][:180]}


def ingest(db, settings, data, filename, metadata, actor_id):
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f'File exceeds the {settings.max_upload_mb} MB upload limit.')
    digest = hashlib.sha256(data).hexdigest()
    if db.documents.find_one({'digest': digest}):
        raise ValueError('This exact document has already been uploaded.')
    if db.documents.find_one({'document_id': metadata['document_id'], 'version': metadata['version']}):
        raise ValueError('This document ID and version already exist. Use a new version for changed content.')
    sections = parse(data, filename)
    doc_id = uid()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    path = settings.upload_dir / (doc_id + Path(filename).suffix.lower())
    path.write_bytes(data)
    record = {'_id': doc_id, **metadata, 'filename': Path(filename).name, 'path': str(path), 'digest': digest,
        'status': 'draft', 'suspicious': any(s['suspicious'] for s in sections), 'created_at': now(), 'created_by': actor_id}
    try:
        db.documents.insert_one(record)
        for block in sections:
            section = {'_id': uid(), 'document_id': doc_id, **block}
            db.source_sections.insert_one(section)
            proposed = candidate(section)
            if proposed:
                key = uid()
                db.requirements.insert_one({'_id': key, 'requirement_id': 'R-' + key[:12].upper(), 'document_id': doc_id,
                    'section_id': block['section_id'], **proposed, 'role_ids': metadata['role_ids'], 'prerequisites': [],
                    'status': 'draft', 'origin': 'source_clause_extraction', 'created_at': now()})
        audit(db, actor_id, 'document.upload', doc_id, {'filename': record['filename'], 'sections': len(sections)})
    except Exception:
        db.requirements.delete_many({'document_id': doc_id})
        db.source_sections.delete_many({'document_id': doc_id})
        db.documents.delete_one({'_id': doc_id})
        path.unlink(missing_ok=True)
        raise
    return record
