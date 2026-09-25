from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
import re
import secrets
from urllib.parse import quote
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo.errors import DuplicateKeyError
from .config import Settings, ROOT
from .db import connect, initialize, now, uid, audit
from .security import (require, identity, csrf, anonymous_csrf, valid_anonymous, new_session,
    verify_password, hash_password, can_read_employee, ROLES, EDITORS, REVIEWERS, token_hash)
from .ingestion import ingest, normalized, SUSPICIOUS
from .schemas import STAGES
from .worker import start_worker, enqueue, matrix
from .training import install_training, current
from .learning import public_content, learning_checks
from .phase3 import install_phase3

templates = Jinja2Templates(directory=str(ROOT/'templates'))


def redirect(path, message=''):
    return RedirectResponse(path + ('?message='+quote(message) if message else ''), status_code=303)


def nonempty(value, label, limit=180):
    value = value.strip()
    if not value or len(value) > limit:
        raise HTTPException(422, f'{label} is required and must be at most {limit} characters.')
    return value


def create_app(settings=None):
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        client, db = connect(settings)
        initialize(db)
        app.state.db = db
        app.state.settings = settings
        worker = start_worker(db, settings) if settings.run_worker else None
        yield
        if worker:
            worker[0].set()
            worker[1].join(timeout=2)
        client.close()

    app = FastAPI(title='SkillSprint AI', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')

    def page(request, name, **context):
        user, session = identity(request)
        return templates.TemplateResponse(request=request, name=name, context={
            'user': user, 'csrf_token': session['csrf'] if session else '', 'message': request.query_params.get('message', ''),
            'path': request.url.path, 'stages': STAGES, 'editors': EDITORS, 'reviewers': REVIEWERS, **context})

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        if not request.url.path.startswith('/static'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        if exc.status_code == 401:
            return redirect('/login', 'Please sign in to continue.')
        response = page(request, 'error.html', error=exc.detail, code=exc.status_code)
        response.status_code = exc.status_code
        return response

    @app.exception_handler(DuplicateKeyError)
    async def duplicate_error(request, exc):
        response = page(request, 'error.html', error='This record already exists. Return and choose a unique value.', code=409)
        response.status_code = 409
        return response

    @app.get('/health')
    def health(request: Request):
        request.app.state.db.command('ping')
        return {'status': 'ok', 'database': 'connected', 'phase': 4}

    @app.get('/login')
    def login_page(request: Request):
        if identity(request)[0]:
            return redirect('/')
        token = anonymous_csrf(settings.app_secret_key)
        response = page(request, 'login.html', login_csrf=token)
        response.set_cookie('login_csrf', token, httponly=True, secure=settings.session_cookie_secure, samesite='strict', max_age=1800)
        return response

    @app.post('/login')
    def login(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
        if not valid_anonymous(csrf_token, request.cookies.get('login_csrf'), settings.app_secret_key):
            raise HTTPException(403, 'Refresh the sign-in page before trying again.')
        db = request.app.state.db
        email = email.strip().lower()[:254]
        ip = request.client.host if request.client else 'unknown'
        key = token_hash(ip+'|'+email)
        window = db.login_limits.find_one({'_id': key, 'expires_at': {'$gt': now()}})
        if window and window['count'] >= 8:
            raise HTTPException(429, 'Too many sign-in attempts. Try again in 15 minutes.')
        if not window:
            db.login_limits.replace_one({'_id': key}, {'_id': key, 'count': 0, 'expires_at': now()+timedelta(minutes=15)}, upsert=True)
        db.login_limits.update_one({'_id': key}, {'$inc': {'count': 1}})
        user = db.users.find_one({'email': email, 'active': True})
        if not user or not verify_password(password, user['password_hash']):
            return redirect('/login', 'Email or password is incorrect.')
        db.login_limits.delete_one({'_id': key})
        token = new_session(db, user['_id'])
        response = redirect('/')
        response.set_cookie('skillsprint_session', token, httponly=True, secure=settings.session_cookie_secure, samesite='lax', max_age=8*3600)
        response.delete_cookie('login_csrf')
        audit(db, user['_id'], 'auth.login', user['_id'])
        return response

    @app.post('/logout')
    def logout(request: Request, csrf_token: str = Form(...)):
        user, session = require(request)
        csrf(request, session, csrf_token)
        request.app.state.db.sessions.delete_one({'_id': session['_id']})
        response = redirect('/login')
        response.delete_cookie('skillsprint_session')
        return response

    def employees_for(db, user):
        query = {}
        if user['role'] == 'employee': query = {'user_id': user['_id']}
        if user['role'] == 'manager': query = {'manager_id': user['_id']}
        return list(db.employees.find(query).sort('name', 1).limit(1000))

    def employee_access(request, employee_id):
        user, session = require(request)
        employee = request.app.state.db.employees.find_one({'_id': employee_id})
        if not employee or not can_read_employee(user, employee):
            raise HTTPException(404, 'Employee not found.')
        return user, session, employee

    @app.get('/')
    def dashboard(request: Request):
        user, _ = require(request)
        db = request.app.state.db
        employees = employees_for(db, user)
        plans = list(db.plans.find({'employee_id': {'$in': [e['_id'] for e in employees]}}, {'matrix_snapshot': 0}).sort('created_at', -1).limit(8))
        stats = {'employees': len(employees), 'plans': db.plans.count_documents({'employee_id': {'$in': [e['_id'] for e in employees]}})}
        if user['role'] in EDITORS | REVIEWERS:
            stats.update(documents=db.documents.count_documents({}), approved=db.requirements.count_documents({'status': 'approved'}))
        return page(request, 'dashboard.html', stats=stats, plans=plans, ai_ready=bool(settings.openai_api_key))

    @app.get('/roles')
    def roles_page(request: Request):
        require(request, EDITORS | REVIEWERS)
        return page(request, 'roles.html', roles=list(request.app.state.db.job_roles.find().sort('name', 1)))

    @app.post('/roles')
    def add_role(request: Request, name: str = Form(...), department: str = Form(...), description: str = Form(''), csrf_token: str = Form(...)):
        user, session = require(request, EDITORS); csrf(request, session, csrf_token)
        role = {'_id': uid(), 'name': nonempty(name, 'Role name'), 'department': nonempty(department, 'Department'),
                'description': description[:2000], 'created_at': now()}
        request.app.state.db.job_roles.insert_one(role)
        audit(request.app.state.db, user['_id'], 'role.create', role['_id'])
        return redirect('/roles', 'Job role created.')

    @app.get('/employees')
    def employees_page(request: Request):
        user, _ = require(request)
        db = request.app.state.db
        return page(request, 'employees.html', employees=employees_for(db,user), roles=list(db.job_roles.find()),
            managers=list(db.users.find({'role': {'$in': ['manager', 'admin']}}, {'password_hash': 0})) if user['role'] in EDITORS else [],
            accounts=list(db.users.find({'role': 'employee'}, {'password_hash': 0})) if user['role'] in EDITORS else [])

    @app.post('/employees')
    def add_employee(request: Request, name: str = Form(...), role_id: str = Form(...), joining_date: str = Form(...),
                     experience: str = Form('Beginner'), manager_id: str = Form(''), user_id: str = Form(''), csrf_token: str = Form(...)):
        user, session = require(request, EDITORS); csrf(request, session, csrf_token)
        db = request.app.state.db
        role = db.job_roles.find_one({'_id': role_id})
        if not role: raise HTTPException(422, 'Choose an existing job role.')
        if experience not in ['Beginner','Intermediate','Advanced']: raise HTTPException(422, 'Invalid experience level.')
        try: date.fromisoformat(joining_date)
        except ValueError: raise HTTPException(422, 'Use a valid joining date.')
        if manager_id and not db.users.find_one({'_id': manager_id, 'role': {'$in': ['admin','manager']}}): raise HTTPException(422, 'Invalid manager account.')
        if user_id and not db.users.find_one({'_id': user_id, 'role': 'employee'}): raise HTTPException(422, 'Invalid employee account.')
        record = {'_id': uid(), 'name': nonempty(name, 'Employee name'), 'role_id': role_id, 'role_name': role['name'], 'department': role['department'],
            'joining_date': joining_date, 'experience': experience, 'manager_id': manager_id, 'user_id': user_id, 'created_at': now()}
        db.employees.insert_one(record); audit(db,user['_id'],'employee.create',record['_id'])
        return redirect('/employees', 'Employee profile created.')

    @app.get('/documents')
    def documents_page(request: Request):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        q = request.query_params.get('q','').strip()[:100]
        query = {'title': {'$regex': re.escape(q), '$options': 'i'}} if q else {}
        return page(request, 'documents.html', documents=list(db.documents.find(query).sort('created_at', -1).limit(100)), roles=list(db.job_roles.find()), q=q)

    @app.post('/documents/upload')
    async def upload(request: Request, file: UploadFile = File(...), document_id: str = Form(...), title: str = Form(...), version: str = Form(...),
        effective_date: str = Form(...), category: str = Form('Policy'), role_id: str = Form(''), csrf_token: str = Form(...)):
        user, session = require(request, EDITORS); csrf(request, session, csrf_token)
        if not re.fullmatch(r'[A-Za-z0-9_-]{2,60}', document_id): raise HTTPException(422,'Document ID must use 2-60 letters, numbers, underscores or hyphens.')
        try: date.fromisoformat(effective_date)
        except ValueError: raise HTTPException(422, 'Use a valid effective date.')
        if role_id and not request.app.state.db.job_roles.find_one({'_id': role_id}): raise HTTPException(422,'Unknown job role.')
        if category not in ['Policy','SOP','Role description','FAQ','Other']: raise HTTPException(422,'Invalid category.')
        data = await file.read(settings.max_upload_mb*1024*1024+1)
        try:
            record = ingest(request.app.state.db, settings, data, file.filename or '',
                {'document_id': document_id, 'title': nonempty(title,'Title'), 'version': nonempty(version,'Version',30), 'effective_date': effective_date,
                 'category': category, 'role_ids': [role_id] if role_id else []}, user['_id'])
        except ValueError as exc: raise HTTPException(422, str(exc)) from None
        except Exception: raise HTTPException(422, 'Unable to parse this document. Check the file and try again.') from None
        return redirect('/documents/'+record['_id'], 'Uploaded. Review the extracted sources and requirement candidates.')

    @app.get('/documents/{document_id}')
    def document_page(request: Request, document_id: str):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        document = db.documents.find_one({'_id': document_id})
        if not document: raise HTTPException(404,'Document not found.')
        return page(request, 'document.html', document=document, sections=list(db.source_sections.find({'document_id':document_id})),
            requirements=list(db.requirements.find({'document_id':document_id})), roles=list(db.job_roles.find()),
            jobs=list(db.jobs.find({'target_id':document_id}).sort('created_at',-1).limit(4)))

    @app.get('/documents/{document_id}/download')
    def download(request: Request, document_id: str):
        require(request, EDITORS | REVIEWERS)
        document = request.app.state.db.documents.find_one({'_id':document_id})
        if not document: raise HTTPException(404,'Document not found.')
        path = Path(document['path']).resolve()
        if not path.is_relative_to(settings.upload_dir) or not path.exists(): raise HTTPException(404,'Original file unavailable.')
        return FileResponse(path, filename=document['filename'], content_disposition_type='attachment')

    @app.post('/documents/{document_id}/activate')
    def activate(request: Request, document_id: str, csrf_token: str = Form(...)):
        user, session = require(request, REVIEWERS); csrf(request,session,csrf_token)
        db = request.app.state.db; document = db.documents.find_one({'_id':document_id})
        if not document: raise HTTPException(404,'Document not found.')
        if document['suspicious']: raise HTTPException(422,'Suspicious source instructions are quarantined. Upload a corrected source.')
        if date.fromisoformat(document['effective_date']) > date.today(): raise HTTPException(422,'A future-dated document cannot be active yet.')
        previous = list(db.documents.find({'document_id':document['document_id'],'status':'active','_id':{'$ne':document_id}}))
        if any(d['effective_date'] >= document['effective_date'] for d in previous):
            raise HTTPException(409,'A newer or same-date active version exists. Resolve precedence before activation.')
        db.documents.update_many({'document_id':document['document_id'],'status':'active','_id':{'$ne':document_id}}, {'$set':{'status':'superseded'}})
        db.documents.update_one({'_id':document_id}, {'$set':{'status':'active','approved_by':user['_id'],'approved_at':now()}})
        db.plans.update_many({'source_document_ids':{'$in':[d['_id'] for d in previous]}},{'$set':{'status':'Stale sources'}})
        audit(db,user['_id'],'document.activate',document_id,{'superseded':[d['_id'] for d in previous]})
        return redirect('/documents/'+document_id,'Document approved and activated. Requirement candidates still need review.')

    @app.post('/documents/{document_id}/extract')
    def extract(request: Request, document_id: str, csrf_token: str = Form(...)):
        user, session = require(request, EDITORS); csrf(request,session,csrf_token)
        document = request.app.state.db.documents.find_one({'_id':document_id})
        if not document: raise HTTPException(404,'Document not found.')
        if document['suspicious']: raise HTTPException(422,'Quarantined source instructions cannot be sent for extraction.')
        job = enqueue(request.app.state.db,user['_id'],'extract',document_id)
        return redirect('/jobs/'+job['_id'])

    @app.post('/requirements/{requirement_id}/review')
    def review(request: Request, requirement_id: str, title: str = Form(...), text: str = Form(...), mandatory: str = Form('false'),
        due_stage: str = Form(...), role_id: str = Form(''), decision: str = Form(...), csrf_token: str = Form(...)):
        user, session = require(request, REVIEWERS); csrf(request,session,csrf_token)
        db = request.app.state.db; req = db.requirements.find_one({'_id':requirement_id})
        if not req: raise HTTPException(404,'Requirement not found.')
        if decision not in ['approved','rejected','draft'] or due_stage not in STAGES: raise HTTPException(422,'Invalid review selection.')
        source = db.source_sections.find_one({'document_id':req['document_id'],'section_id':req['section_id']})
        doc = db.documents.find_one({'_id':req['document_id']})
        clean = normalized(text)
        if not clean or len(clean)>6000 or clean not in normalized(source['text']): raise HTTPException(422,'Requirement text must be an exact passage from its source section.')
        if decision=='approved' and (doc['status']!='active' or doc['suspicious'] or SUSPICIOUS.search(clean)):
            raise HTTPException(422,'Activate a safe source document before approving its requirements.')
        if role_id and not db.job_roles.find_one({'_id':role_id}): raise HTTPException(422,'Unknown job role.')
        changes = {'title':nonempty(title,'Requirement title'), 'text':clean, 'mandatory':mandatory=='true', 'due_stage':due_stage,
                   'role_ids':[role_id] if role_id else [], 'status':decision, 'reviewed_by':user['_id'], 'reviewed_at':now()}
        db.requirements.update_one({'_id':requirement_id},{'$set':changes})
        db.plans.update_many({'source_document_ids':req['document_id']},{'$set':{'status':'Stale sources'}})
        audit(db,user['_id'],'requirement.review',requirement_id,{'before':{k:req.get(k) for k in changes},'after':changes})
        return redirect('/documents/'+req['document_id'],'Review saved with the original values in the audit trail.')

    @app.get('/matrix')
    def matrix_page(request: Request):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db; roles=list(db.job_roles.find())
        role_id=request.query_params.get('role_id',roles[0]['_id'] if roles else '')
        return page(request,'matrix.html',roles=roles,role_id=role_id,requirements=matrix(db,role_id) if role_id else [])

    @app.post('/employees/{employee_id}/generate')
    def generate(request: Request, employee_id: str, csrf_token: str = Form(...)):
        user,session = require(request,EDITORS); csrf(request,session,csrf_token)
        if not request.app.state.db.employees.find_one({'_id':employee_id}): raise HTTPException(404,'Employee not found.')
        job=enqueue(request.app.state.db,user['_id'],'generate',employee_id)
        return redirect('/jobs/'+job['_id'])

    def job_access(request,job_id):
        user,_=require(request)
        job=request.app.state.db.jobs.find_one({'_id':job_id})
        if not job or (job['actor_id']!=user['_id'] and user['role']!='admin'): raise HTTPException(404,'Job not found.')
        return job

    @app.get('/jobs/{job_id}')
    def job_page(request: Request,job_id: str):
        return page(request,'job.html',job=job_access(request,job_id))

    @app.get('/jobs/{job_id}/status')
    def job_status(request: Request,job_id: str):
        job=job_access(request,job_id)
        return {'status':job['status']}

    @app.get('/plans')
    def plans_page(request: Request):
        user,_=require(request); db=request.app.state.db
        employees=employees_for(db,user)
        return page(request,'plans.html',plans=list(db.plans.find({'employee_id':{'$in':[e['_id'] for e in employees]}},{'matrix_snapshot':0}).sort('created_at',-1).limit(100)), employees={e['_id']:e for e in employees})

    def plan_access(request,plan_id):
        plan=request.app.state.db.plans.find_one({'_id':plan_id})
        if not plan: raise HTTPException(404,'Plan not found.')
        employee_access(request,plan['employee_id'])
        return plan

    @app.get('/plans/{plan_id}')
    def plan_page(request: Request,plan_id: str):
        plan=plan_access(request,plan_id)
        db=request.app.state.db
        employee=db.employees.find_one({'_id':plan['employee_id']})
        user,_=require(request)
        if user['role']=='employee': plan['content']=public_content(plan['content'])
        return page(request,'plan.html',plan=plan,employee=employee,
            teaching=plan.get('learning_checks') or learning_checks(plan['content']),
            fresh=current(db,plan,employee), decisions=list(db.plan_reviews.find({'plan_id':plan_id}).sort('created_at',1)))

    @app.get('/plans/{plan_id}/json')
    def plan_json(request: Request,plan_id: str):
        plan=plan_access(request,plan_id)
        user,_=require(request)
        content=public_content(plan['content']) if user['role']=='employee' else plan['content']
        return JSONResponse({'plan':content,'validation':plan['validation'],'status':plan['status'],
            'model':plan['model'],'prompt_version':plan['prompt_version'], 'origin':plan.get('origin','ai_generation'),
            'parent_plan_id':plan.get('parent_plan_id'),
            'published_at':plan['published_at'].isoformat() if plan.get('published_at') else None},
            headers={'Content-Disposition':'attachment; filename="plan.json"'})

    @app.get('/users')
    def users_page(request: Request):
        require(request,{'admin'})
        return page(request,'users.html',users=list(request.app.state.db.users.find({}, {'password_hash':0})),account_roles=sorted(ROLES))

    @app.post('/users')
    def add_user(request: Request,email: str=Form(...),name: str=Form(...),password: str=Form(...),role: str=Form(...),csrf_token: str=Form(...)):
        user,session=require(request,{'admin'});csrf(request,session,csrf_token)
        if role not in ROLES: raise HTTPException(422,'Invalid account role.')
        email=email.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254: raise HTTPException(422,'Enter a valid email address.')
        try: encoded=hash_password(password)
        except ValueError as exc: raise HTTPException(422,str(exc)) from None
        key=uid();request.app.state.db.users.insert_one({'_id':key,'email':email,'name':nonempty(name,'Name'),
            'password_hash':encoded,'role':role,'active':True,'created_at':now()})
        audit(request.app.state.db,user['_id'],'user.create',key,{'role':role})
        return redirect('/users','Account created. Share its login details privately.')

    @app.get('/audit')
    def audit_page(request: Request):
        require(request,REVIEWERS)
        return page(request,'audit.html',events=list(request.app.state.db.audit_events.find().sort('created_at',-1).limit(100)))

    install_training(app,page,employees_for,employee_access,plan_access)
    install_phase3(app,page,employees_for,employee_access,plan_access)
    return app
