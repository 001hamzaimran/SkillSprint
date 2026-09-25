"""Disposable browser QA server. All records are explicitly synthetic test data."""
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from app.config import Settings, ROOT
from app.db import connect, initialize, now
from app.security import hash_password
from app.main import create_app
from app.schemas import FullOnboardingPlan
from app.worker import fingerprint
from app.validation import validate_plan
from app.learning import learning_checks
from tests.test_phase2 import full_item


def main():
    settings=Settings().model_copy(update={'mongodb_db_name':'skillsprint_browser_phase2_'+uuid4().hex,
        'run_worker':False, 'port':8001, 'upload_dir':ROOT/'tmp'/'browser_phase2_uploads'})
    client,db=connect(settings);initialize(db)
    try:
        for role in ['admin','employee']:
            db.users.insert_one({'_id':role,'email':role+'@browser.test','name':'Browser '+role.title(),'role':role,
                'active':True,'password_hash':hash_password('Browser-Phase2-Test!2026'),'created_at':now()})
        db.job_roles.insert_one({'_id':'role','name':'Support','department':'Support'})
        db.employees.insert_one({'_id':'learner','name':'Fictional QA Learner','role_id':'role','role_name':'Support','department':'Support',
            'experience':'Beginner','joining_date':str(now().date()),'user_id':'employee','manager_id':'admin'})
        source='Employees must lock their workstations before leaving them.'
        doc={'_id':'doc','document_id':'QA-01','version':'1','title':'Synthetic browser QA policy','status':'active','digest':'qa','suspicious':False}
        section={'_id':'section','document_id':'doc','section_id':'s1','text':source}
        req={'_id':'req','requirement_id':'QA-R1','document_id':'doc','section_id':'s1','text':source,'status':'approved',
             'mandatory':True,'role_ids':['role'],'due_stage':'Week 1','title':'Lock workstations','prerequisites':[]}
        db.documents.insert_one(doc);db.source_sections.insert_one(section);db.requirements.insert_one(req)
        item=full_item({'requirement_id':'QA-R1','source_document_id':'doc','source_section_id':'s1','text':source,'mandatory':True})
        item['scenario']['expected_response']='Lock the workstation before leaving it.'
        item['quiz']['explanation']='Locking your screen protects information while you are away, as the policy requires.'
        content=FullOnboardingPlan(title='Your first week in Support',summary='Synthetic browser test: practice protecting your workspace.',role_id='role',items=[item])
        db.plans.insert_one({'_id':'qa-plan','employee_id':'learner','role_id':'role','content':content.model_dump(),
            'status':'Review required','validation':validate_plan(content,[req],[doc],[section],'role'),
            'learning_checks':learning_checks(content.model_dump()),'matrix_snapshot':[req],'snapshot_digest':fingerprint([req]),
            'source_document_ids':['doc'],'model':'EXPLICIT TEST FIXTURE','prompt_version':'generate_v2','generation':{},'created_at':now(),'created_by':'admin'})
        print('Disposable Phase 2 browser QA server on http://127.0.0.1:8001',flush=True)
        uvicorn.run(create_app(settings),host='127.0.0.1',port=8001)
    finally:
        assert db.name.startswith('skillsprint_browser_phase2_')
        client.drop_database(db.name);client.close()


if __name__=='__main__': main()
