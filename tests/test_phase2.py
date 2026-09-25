from copy import deepcopy
from html.parser import HTMLParser
import pytest
from app.db import now
from app.worker import enqueue, process_one, matrix, fingerprint
from app.learning import progress_report, learning_checks
from app.schemas import FullOnboardingPlan
from app.validation import validate_plan
from .conftest import login, upload_docx
from .test_phase1 import approve


def full_item(r, role='role'):
    return {'requirement_id':r['requirement_id'], 'role_id':role, 'source_document_id':r['source_document_id'],
        'source_section_id':r['source_section_id'], 'source_quote':r['text'], 'mandatory':r['mandatory'], 'stage':'Week 1',
        'module_title':'Workstation security', 'learning_objective':'Apply the locking rule', 'practical_activity':'Describe a simulated screen-lock check.',
        'estimated_minutes':10, 'lesson':'Protect information on your workstation by applying this policy before stepping away. Use a fictional practice session.',
        'checklist':['Read the approved policy.', 'Practice locking a fictional workstation.'],
        'scenario':{'prompt':'You are leaving your workstation. What should you do?', 'expected_response':'EXPECTED_RESPONSE_SECRET: Lock it first.'},
        'quiz':{'question':'Which action protects an unattended workstation?', 'options':['Lock the screen','Leave it unlocked','Share the password'],
                'correct_index':0, 'explanation':'ANSWER_KEY_SECRET: Follow the approved workstation locking rule.', 'evidence_quote':r['text']},
        'rubric':[{'criterion':'Scenario applies the locking rule.','max_points':5}, {'criterion':'Practical work describes a locking check.','max_points':5}]}


@pytest.fixture
def training(workspace):
    client, db, settings=workspace
    token=login(client); upload_docx(client,token)
    approve(client,db,token,db.documents.find_one({}))
    db.job_roles.insert_one({'_id':'role','name':'Support','department':'Support'})
    db.employees.insert_one({'_id':'learner','name':'Test Learner','role_id':'role','role_name':'Support','department':'Support',
        'experience':'Beginner','joining_date':'2026-01-01','user_id':'employee','manager_id':'manager'})
    def provider(settings,schema,template,payload,on_attempt):
        assert template=='generate_v3.txt'
        return FullOnboardingPlan(title='TEST DOUBLE learning plan',summary='Explicit test fixture, not live AI evidence.',
            role_id='role',items=[full_item(r) for r in payload['requirements']]), {'model':'TEST_DOUBLE','attempts':1}
    job=enqueue(db,'admin','generate','learner');process_one(db,settings,provider=provider)
    assert db.jobs.find_one({'_id':job['_id']})['status']=='completed'
    plan=db.plans.find_one({'_id':job['_id']})
    assert plan['learning_checks']['passed']
    yield client,db,settings,plan,token


def publish(client,plan,token):
    return client.post('/plans/'+plan['_id']+'/review',data={'csrf_token':token,'decision':'approve',
        'comment':'Test reviewer checked all teaching content and answers.', 'confirmed':'true'})


def test_review_requires_role_confirmation_valid_content_and_current_matrix(training):
    client,db,_,plan,token=training
    path='/plans/'+plan['_id']+'/review'
    assert client.post(path,data={'csrf_token':token,'decision':'approve','comment':'Review'}).status_code==422
    token=login(client,'training_manager');assert publish(client,plan,token).status_code==403
    token=login(client,'reviewer')
    assert client.post(path,data={'csrf_token':token,'decision':'reject','comment':'Please clarify the activity.'}).status_code==200
    assert db.plans.find_one({'_id':plan['_id']})['status']=='Rejected'
    assert publish(client,plan,token).status_code==200
    assert db.employees.find_one({'_id':'learner'})['active_plan_id']==plan['_id']
    assert publish(client,plan,token).status_code==409
    assert client.post(path,data={'csrf_token':token,'decision':'comment','comment':'Published content checked.'}).status_code==200
    assert db.plan_reviews.count_documents({'plan_id':plan['_id']})==3
    assert db.plans.find_one({'_id':plan['_id']})['validation']==plan['validation']


def test_review_form_exposes_all_decisions(training):
    client,db,_,plan,token=training
    class DecisionOptions(HTMLParser):
        inside=False
        values=[]
        def handle_starttag(self,tag,attrs):
            attributes=dict(attrs)
            if tag=='select': self.inside=attributes.get('name')=='decision'
            if tag=='option' and self.inside: self.values.append(attributes.get('value'))
        def handle_endtag(self,tag):
            if tag=='select': self.inside=False
    parser=DecisionOptions();parser.feed(client.get('/plans/'+plan['_id']).text)
    assert set(parser.values)=={'approve','reject','comment'}


def test_learner_cannot_see_answer_keys_or_submit_drafts(training):
    client,db,_,plan,_=training;token=login(client,'employee')
    base='/learning/'+plan['_id']; req=plan['content']['items'][0]['requirement_id']
    for url in ['/plans/'+plan['_id'], '/plans/'+plan['_id']+'/json',base]:
        response=client.get(url);assert response.status_code==200
        assert 'ANSWER_KEY_SECRET' not in response.text
        assert 'EXPECTED_RESPONSE_SECRET' not in response.text
        assert 'correct_index' not in response.text
    assert client.post(base+'/'+req+'/quiz',data={'csrf_token':token,'answer':0}).status_code==409
    assert client.get('/assessments').status_code==403
    assert client.get('/plans/'+plan['_id']+'/items/'+req+'/edit').status_code==403


def test_full_learning_grading_retry_and_progress_flow(training):
    client,db,_,plan,token=training;assert publish(client,plan,token).status_code==200
    token=login(client,'employee'); req=plan['content']['items'][0]['requirement_id']; base='/learning/'+plan['_id']+'/'+req
    assert client.post(base+'/progress',data={'csrf_token':token,'lesson_read':'true','checked':['0','1']}).status_code==200
    assert client.post(base+'/quiz',data={'csrf_token':token,'answer':'1','score':'100','passed':'true'}).status_code==200
    assert db.quiz_attempts.find_one({})['score']==0
    report=progress_report(db,plan,db.employees.find_one({'_id':'learner'})); assert len(report['weak'])==1 and report['percent']==0
    assert client.post(base+'/quiz',data={'csrf_token':token,'answer':'0'}).status_code==200
    data={'csrf_token':token,'scenario_response':'I would lock my screen.','practical_response':'I practiced a simulated lock check.'}
    assert client.post(base+'/submit',data=data).status_code==200
    assert client.post(base+'/submit',data=data).status_code==409
    submission=db.practical_submissions.find_one({})
    assert client.post('/submissions/'+submission['_id']+'/grade',data={'csrf_token':token,'score_0':'5','score_1':'5','feedback':'Self grade'}).status_code==403
    token=login(client,'manager'); assert client.get('/assessments').status_code==200
    grade={'csrf_token':token,'score_0':'1','score_1':'2','feedback':'Explain how you verify the lock actually worked.'}
    assert client.post('/submissions/'+submission['_id']+'/grade',data=grade).status_code==200
    assert client.post('/submissions/'+submission['_id']+'/grade',data=grade).status_code==409
    token=login(client,'employee'); data['csrf_token']=token
    assert 'Explain how you verify' in client.get('/learning/'+plan['_id']).text
    assert client.post(base+'/submit',data=data).status_code==200
    pending=db.practical_submissions.find_one({'status':'pending'})
    token=login(client,'reviewer')
    grade.update(csrf_token=token,score_0='5',score_1='5',feedback='Both responses correctly demonstrate the published rule.')
    assert client.post('/submissions/'+pending['_id']+'/grade',data=grade).status_code==200
    report=progress_report(db,plan,db.employees.find_one({'_id':'learner'}))
    assert report['percent']==100 and report['mandatory_complete'] and not report['weak']
    assert len(report['rows'][0]['submissions'])==2
    # Learning records are persisted, not session state.
    login(client,'employee');assert '100%' in client.get('/learning/'+plan['_id']).text
    assert db.audit_events.count_documents({'action':'learning.grade'})==2


def edit_form(item,token):
    form={'csrf_token':token, **{key:item[key] for key in ['module_title','learning_objective','lesson','practical_activity','stage','estimated_minutes']},
        'checklist':'\n'.join(item['checklist']),'scenario_prompt':item['scenario']['prompt'],'scenario_expected':item['scenario']['expected_response'],
        'question':item['quiz']['question'],'options':'\n'.join(item['quiz']['options']),'correct_index':item['quiz']['correct_index'],
        'explanation':item['quiz']['explanation'],'reason':'Clarified wording for the learner.'}
    for i,rule in enumerate(item['rubric']): form.update({f'criterion_{i}':rule['criterion'], f'points_{i}':rule['max_points']})
    return form


def test_edits_make_new_validated_drafts_and_preserve_publication(training):
    client,db,_,plan,token=training; publish(client,plan,token)
    item=plan['content']['items'][0]; form=edit_form(item,token); form['module_title']='A clearer module title'
    path='/plans/'+plan['_id']+'/items/'+item['requirement_id']+'/edit'
    assert client.get(path).status_code==200
    assert client.post(path,data=form).status_code==200
    new=db.plans.find_one({'parent_plan_id':plan['_id']})
    assert new['status']=='Review required' and new['validation']['core_passed']
    assert db.plans.find_one({'_id':plan['_id']})['content']==plan['content']
    assert db.employees.find_one({'_id':'learner'})['active_plan_id']==plan['_id']
    form['correct_index']='4';assert client.post(path,data=form).status_code==422
    assert publish(client,new,token).status_code==200
    token=login(client,'employee')
    assert client.post('/learning/'+plan['_id']+'/'+item['requirement_id']+'/quiz',data={'csrf_token':token,'answer':0}).status_code==409


def test_publication_blocks_bad_assessments_and_stale_sources(training):
    client,db,_,plan,token=training
    bad=deepcopy(plan['content']);bad['items'][0]['quiz']['evidence_quote']='Invented evidence.'
    assert not learning_checks(bad)['passed']
    db.plans.update_one({'_id':plan['_id']},{'$set':{'content':bad}})
    assert publish(client,plan,token).status_code==409
    db.plans.update_one({'_id':plan['_id']},{'$set':{'content':plan['content']}})
    db.requirements.update_one({}, {'$set':{'mandatory':False}})
    assert publish(client,plan,token).status_code==409


def test_cross_employee_access_and_score_bounds(training):
    client,db,_,plan,token=training; publish(client,plan,token)
    token=login(client,'employee'); req=plan['content']['items'][0]['requirement_id']; base='/learning/'+plan['_id']+'/'+req
    assert client.post(base+'/progress',data={'csrf_token':token,'checked':['999']}).status_code==422
    assert client.post(base+'/quiz',data={'csrf_token':'wrong','answer':0}).status_code==403
    assert client.post(base+'/quiz',data={'csrf_token':token,'answer':7}).status_code==422
    assert client.post(base+'/submit',data={'csrf_token':token,'scenario_response':'Answer','practical_response':'Evidence'}).status_code==200
    submission=db.practical_submissions.find_one({})
    token=login(client,'manager')
    assert client.post('/submissions/'+submission['_id']+'/grade',data={'csrf_token':token,'score_0':999,'score_1':5,'feedback':'Test feedback'}).status_code==422
    db.employees.update_one({'_id':'learner'},{'$set':{'manager_id':'other-manager'}})
    assert client.get('/learning/'+plan['_id']).status_code==404
    assert client.post('/submissions/'+submission['_id']+'/grade',data={'csrf_token':token,'score_0':5,'score_1':5,'feedback':'Test feedback'}).status_code==404
    login(client,'employee'); db.employees.update_one({'_id':'learner'},{'$set':{'user_id':'other-user'}})
    assert client.get('/learning/'+plan['_id']).status_code==404


def test_source_change_blocks_already_published_learning(training):
    client,db,_,plan,token=training;publish(client,plan,token)
    db.requirements.update_one({}, {'$set':{'due_stage':'Day 1'}})
    token=login(client,'employee'); req=plan['content']['items'][0]['requirement_id']
    assert client.post('/learning/'+plan['_id']+'/'+req+'/quiz',data={'csrf_token':token,'answer':0}).status_code==409
    assert 'Read-only history' in client.get('/learning/'+plan['_id']).text


def test_link_existing_employee_to_unique_account(training):
    client,db,_,plan,token=training
    db.employees.insert_one({'_id':'second','name':'Other','role_id':'role','department':'Support'})
    assert client.post('/employees/second/account',data={'csrf_token':token,'user_id':'employee'}).status_code==409
    assert client.post('/employees/learner/account',data={'csrf_token':token,'user_id':''}).status_code==200
    assert client.post('/employees/second/account',data={'csrf_token':token,'user_id':'employee'}).status_code==200


def test_prerequisites_block_learning_until_completed(training):
    client,db,_,plan,token=training
    first=plan['content']['items'][0]
    requirement=deepcopy(plan['matrix_snapshot'][0])
    requirement.update(_id='dependent',requirement_id='R-DEPENDENT',prerequisites=[first['requirement_id']])
    db.requirements.insert_one(requirement)
    dependent=deepcopy(first);dependent['requirement_id']='R-DEPENDENT'
    content=deepcopy(plan['content']);content['items'].append(dependent)
    requirements=matrix(db,'role')
    validation=validate_plan(FullOnboardingPlan.model_validate(content),requirements,list(db.documents.find()),list(db.source_sections.find()),'role')
    db.plans.update_one({'_id':plan['_id']},{'$set':{'content':content,'matrix_snapshot':requirements,
        'snapshot_digest':fingerprint(requirements),'validation':validation}})
    assert publish(client,plan,token).status_code==200
    token=login(client,'employee')
    assert client.post('/learning/'+plan['_id']+'/R-DEPENDENT/quiz',data={'csrf_token':token,'answer':0}).status_code==409
    assert 'Complete these prerequisites first' in client.get('/learning/'+plan['_id']).text
    assert client.post('/learning/'+plan['_id']+'/'+first['requirement_id']+'/quiz',data={'csrf_token':token,'answer':0}).status_code==200


def test_generation_batches_all_requirements_and_renews_lease(training):
    client,db,settings,plan,token=training
    original=plan['matrix_snapshot'][0]
    for i in range(5):
        req=deepcopy(original);req.update(_id='batch'+str(i),requirement_id='R-BATCH'+str(i));db.requirements.insert_one(req)
    calls=[]
    def provider(settings,schema,template,payload,on_attempt):
        calls.append(len(payload['requirements']))
        on_attempt(1,'TEST_DOUBLE')
        return FullOnboardingPlan(title='Batched fixture',summary='Test-only batch coverage.',role_id='role',
            items=[full_item(r) for r in payload['requirements']]),{'model':'TEST_DOUBLE','attempts':1}
    job=enqueue(db,'admin','generate','learner');process_one(db,settings,provider)
    assert calls==[4,2]
    result=db.plans.find_one({'_id':job['_id']})
    assert len(result['content']['items'])==6 and result['validation']['coverage']==100
    assert len(result['generation']['batches'])==2
