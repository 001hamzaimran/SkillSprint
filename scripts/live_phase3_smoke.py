"""Real Phase 3 API evaluation; fictional sources and isolated disposable MongoDB.

Makes four small generation calls under normal conditions: initial plan, two
controlled repeats, and one selective update. Test approvals and learning records
are explicitly synthetic and do not certify real competency or human review.
"""
import io
import json
import sys
import time
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from docx import Document
from fastapi.testclient import TestClient
from app.config import Settings, ROOT
from app.main import create_app
from app.db import now
from app.security import hash_password
from app.worker import process_one
from tests.conftest import csrf


def main():
    settings=Settings().model_copy(update={'mongodb_db_name':'skillsprint_phase3_live_'+uuid4().hex,
        'run_worker':False,'upload_dir':ROOT/'tmp'/'phase3_live_uploads'})
    if not settings.openai_api_key: raise SystemExit('Configure OPENAI_API_KEY locally first.')
    app=create_app(settings); report={'phase':3,'timestamp':now().isoformat(),'provider':settings.genai_provider,'model':settings.genai_model,
        'note':'Real API output; automated test approvals and seeded learning history are synthetic, not human verification.'}
    started=time.perf_counter()
    with TestClient(app) as client:
        db=app.state.db
        try:
            password=uuid4().hex
            db.users.insert_one({'_id':'admin','email':'phase3@test.local','name':'Isolated test reviewer','role':'admin',
                'password_hash':hash_password(password),'active':True,'created_at':now()})
            response=client.post('/login',data={'email':'phase3@test.local','password':password,'csrf_token':csrf(client.get('/login').text)})
            token=csrf(response.text)
            db.job_roles.insert_one({'_id':'support','name':'Fictional Support','department':'Support'})
            db.employees.insert_one({'_id':'learner','name':'Fictional test learner','role_id':'support','role_name':'Fictional Support',
                'department':'Support','experience':'Beginner','joining_date':'2026-09-24','manager_id':'admin','user_id':''})

            def source(identifier,body,version,value,condition='',exception=''):
                document=Document();document.add_paragraph(body);stream=io.BytesIO();document.save(stream)
                response=client.post('/documents/upload',data={'csrf_token':token,'document_id':identifier,'title':'Fictional '+identifier,
                    'version':version,'effective_date':'2026-01-01' if version=='1' else '2026-02-01','category':'Policy','role_id':'support'},
                    files={'file':('policy.docx',stream.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
                assert response.status_code==200
                doc=db.documents.find_one({'document_id':identifier,'version':version})
                assert client.post('/documents/'+doc['_id']+'/activate',data={'csrf_token':token}).status_code==200
                req=db.requirements.find_one({'document_id':doc['_id']})
                assert client.post('/requirements/'+req['_id']+'/review',data={'csrf_token':token,'title':identifier,'text':req['text'],
                    'mandatory':'true','due_stage':'Week 1','role_id':'support','decision':'approved'}).status_code==200
                assert client.post('/requirements/'+req['_id']+'/rules',data={'csrf_token':token,'key':identifier.lower(),
                    'value':value,'condition':condition,'exception':exception,'answer_fact':value,'module_category':identifier,
                    'assessment_topic':identifier+' action','reason':'Automated exact-excerpt mapping for isolated integration testing.'}).status_code==200
                return db.requirements.find_one({'_id':req['_id']})

            lock=source('LOCK-01','Employees must lock their workstation before leaving it unattended.','1','lock their workstation')
            source('ACK-01','During a shift, employees must acknowledge a case within 2 working hours. Urgent incidents require immediate escalation.',
                '1','2 working hours','During a shift','Urgent incidents require immediate escalation.')
            assert client.post('/employees/learner/generate',data={'csrf_token':token}).status_code==200
            process_one(db,settings)
            job=db.jobs.find_one({});assert job['status']=='completed',job.get('error')
            base=db.plans.find_one({'_id':job['result_id']})
            report['initial']={'generation':base['generation'],'validation':base['validation'],'content':base['content']}
            assert base['validation']['core_passed'],base['validation']['findings']
            assert client.post('/plans/'+base['_id']+'/consistency',data={'csrf_token':token}).status_code==200
            experiment=db.consistency_experiments.find_one({})
            process_one(db,settings);process_one(db,settings)
            response=client.get('/experiments/'+experiment['_id']+'/json');assert response.status_code==200,response.text
            report['consistency']=response.json()
            assert report['consistency']['comparison']['comparable']

            def publish(plan):
                result=client.post('/plans/'+plan['_id']+'/review',data={'csrf_token':token,'decision':'approve','confirmed':'true',
                    'comment':'Automated publication-path test in disposable database; human verification remains pending.'})
                assert result.status_code==200,result.text
            publish(base)
            item=next(i for i in base['content']['items'] if i['requirement_id']==lock['requirement_id'])
            identity={'plan_id':base['_id'],'employee_id':'learner','requirement_id':lock['requirement_id']}
            db.learning_progress.insert_one({'_id':'synthetic-progress',**identity,'lesson_read':True,'checked':list(range(len(item['checklist'])))})
            db.quiz_attempts.insert_one({'_id':'synthetic-quiz',**identity,'answer':item['quiz']['correct_index'],'score':100,'passed':True,
                'feedback':'Explicit synthetic migration fixture.','created_at':now()})
            db.practical_submissions.insert_one({'_id':'synthetic-assessment',**identity,'status':'graded','passed':True,'percent':100,
                'scores':[r['max_points'] for r in item['rubric']],'feedback':'Explicit synthetic migration fixture.',
                'scenario_response':'Synthetic response','practical_response':'Synthetic evidence','created_at':now()})
            source('ACK-01','During a shift, employees must acknowledge a case within 1 working hour. Urgent incidents require immediate escalation.',
                '2','1 working hour','During a shift','Urgent incidents require immediate escalation.')
            assert client.post('/plans/'+base['_id']+'/update',data={'csrf_token':token}).status_code==200
            process_one(db,settings)
            job=db.jobs.find_one({'kind':'selective'});assert job['status']=='completed',job.get('error')
            updated=db.plans.find_one({'_id':job['result_id']})
            report['selective_attempt']={'generation':updated['generation'],'validation':updated['validation'],'content':updated['content']}
            assert updated['validation']['core_passed'],updated['validation']['findings']
            assert updated['update_delta']['retained']==[lock['requirement_id']] and len(updated['update_delta']['regenerate'])==1
            publish(updated)
            counts={name:db[name].count_documents({'plan_id':updated['_id']}) for name in ('learning_progress','quiz_attempts','practical_submissions')}
            assert all(count==1 for count in counts.values())
            assert client.get('/reports.csv').status_code==200
            assert client.get('/plans/'+updated['_id']+'/validation.csv').status_code==200
            report['selective']={'generation':updated['generation'],'validation':updated['validation'],'content':updated['content'],
                'delta':updated['update_delta'],'carried_records':counts}
            report.update(status='passed',elapsed_seconds=round(time.perf_counter()-started,2))
        except Exception as error:
            report.update(status='failed',error_type=type(error).__name__,
                failed_jobs=[{'status':j['status'],'error':j.get('error')} for j in db.jobs.find({'status':'failed'})])
            raise
        finally:
            (ROOT/'reports'/'phase3_live_smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            assert db.name.startswith('skillsprint_phase3_live_')
            db.client.drop_database(db.name)
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],
        'consistency_score':report['consistency']['comparison']['consistency_score'],
        'retained_modules':len(report['selective']['delta']['retained']),
        'regenerated_modules':len(report['selective']['delta']['regenerate']),
        'carried_records':report['selective']['carried_records']}))


if __name__=='__main__': main()
