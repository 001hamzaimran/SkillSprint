"""Opt-in real OpenAI integration check using an isolated local test database.

Uses only fictional company source material and .env credentials. Does not log
keys, raw exceptions, or private application data. Results are genuine provider
evidence, not fixtures. Estimated provider usage is one small generation request.
"""
import json
import sys
import time
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.config import Settings, ROOT
from app.main import create_app
from app.db import now
from app.security import hash_password
from app.worker import process_one
from tests.conftest import csrf

def main():
    settings=Settings()
    if not settings.openai_api_key:
        raise SystemExit('API key is not configured.')
    settings=settings.model_copy(update={'mongodb_db_name':'skillsprint_live_test_'+uuid4().hex,'run_worker':False,
        'upload_dir':ROOT/'tmp'/'live_smoke_uploads'})
    app=create_app(settings)
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    with TestClient(app) as client:
        db=app.state.db
        try:
            password=uuid4().hex
            db.users.insert_one({'_id':'smoke-admin','email':'smoke@test.local','name':'Smoke reviewer','role':'admin',
                'active':True,'password_hash':hash_password(password),'created_at':now()})
            page=client.get('/login')
            response=client.post('/login',data={'email':'smoke@test.local','password':password,'csrf_token':csrf(page.text)})
            token=csrf(response.text)
            client.post('/roles',data={'name':'Customer Support Executive','department':'Customer Experience','csrf_token':token})
            role=db.job_roles.find_one({})
            client.post('/employees',data={'name':'Fictional Smoke Learner','role_id':role['_id'],'joining_date':'2026-09-24','experience':'Beginner','csrf_token':token})
            employee=db.employees.find_one({})
            path=ROOT/'sample_documents/asterbridge/current/SOP-11_v1_0.pdf'
            response=client.post('/documents/upload',data={'document_id':'SOP-11','title':'Customer Support Case Handling Procedure','version':'1.0',
                'effective_date':'2026-09-01','category':'SOP','role_id':role['_id'],'csrf_token':token},files={'file':(path.name,path.read_bytes(),'application/pdf')})
            assert response.status_code==200
            doc=db.documents.find_one({})
            response=client.post('/documents/'+doc['_id']+'/activate',data={'csrf_token':token});assert response.status_code==200
            for req in db.requirements.find({}):
                response=client.post('/requirements/'+req['_id']+'/review',data={'csrf_token':token,'title':req['title'],'text':req['text'],
                    'mandatory':str(req['mandatory']).lower(),'due_stage':'Week 1','role_id':role['_id'],'decision':'approved'})
                assert response.status_code==200
            response=client.post('/employees/'+employee['_id']+'/generate',data={'csrf_token':token});assert response.status_code==200
            started=time.perf_counter();process_one(db,settings);elapsed=round(time.perf_counter()-started,2)
            job=db.jobs.find_one({})
            report={'test':'Real OpenAI Phase 1 integration','timestamp':now().isoformat(),'provider':'openai','model':settings.genai_model,
                'database':'isolated local MongoDB','upload_format':'PDF','source':'AsterBridge SOP-11 v1.0',
                'requirements_approved':db.requirements.count_documents({'status':'approved'}),'status':job['status'],'elapsed_seconds':elapsed}
            if job['status']=='completed':
                plan=db.plans.find_one({})
                report.update({'generation':plan['generation'],'validation':plan['validation'],'plan':plan['content']})
                assert client.get('/plans/'+plan['_id']).status_code==200
                assert client.get('/plans/'+plan['_id']+'/json').status_code==200
            else:
                report['error']=job.get('error','Unknown safe failure')
            (out/'phase1_live_smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k not in ['plan','validation','generation']}))
            if 'validation' in report:
                print(json.dumps({k:report['validation'][k] for k in ['coverage','traceability','core_passed','status']}))
            return 0 if job['status']=='completed' else 1
        finally:
            assert db.name.startswith('skillsprint_live_test_')
            db.client.drop_database(db.name)

if __name__=='__main__':
    raise SystemExit(main())
