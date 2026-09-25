from copy import deepcopy
from datetime import timedelta
import csv
import io
import pytest
from app.db import now
from app.policy import matrix_state, matrix, fingerprint, selective_delta, dependency_findings
from app.schemas import FullOnboardingPlan
from app.validation import validate_plan
from app.worker import enqueue, process_one
from app.comparison import compare_plans
from app.updates import carry_progress
from .conftest import login, upload_docx
from .test_phase1 import approve
from .test_phase2 import training, full_item, publish, edit_form


def provider(settings,schema,template,payload,on_attempt):
    items=[]
    for requirement in payload['requirements']:
        item=full_item(requirement, payload['employee']['role_id'])
        rule=requirement.get('policy_rule')
        if rule:
            item['policy_facts']=rule
            item['lesson']+=' '+rule['condition']+' '+rule['exception']
            if rule['answer_fact']: item['quiz']['options'][0]=rule['answer_fact']
        items.append(item)
    return FullOnboardingPlan(title='EXPLICIT Phase 3 test provider',summary='Synthetic test data, not real AI output.',
        role_id=payload['employee']['role_id'],items=items),{'model':'TEST_DOUBLE','attempts':1}


def annotate_data(token, **overrides):
    return {'csrf_token':token,'key':'workstation.lock','value':'lock','condition':'','exception':'','answer_fact':'lock',
        'module_category':'Security','assessment_topic':'Workstation locking','prerequisites':'','reason':'Test reviewer maps this exact source excerpt.',**overrides}


def test_annotations_enforce_source_excerpts_permissions_and_snapshot_changes(training):
    client,db,_,plan,token=training;req=db.requirements.find_one({});before=fingerprint([req])
    path='/requirements/'+req['_id']+'/rules'
    assert client.post(path,data=annotate_data(token,value='invented deadline')).status_code==422
    assert client.post(path,data=annotate_data(token)).status_code==200
    assert fingerprint([db.requirements.find_one({'_id':req['_id']})])!=before
    assert db.plans.find_one({'_id':plan['_id']})['status']=='Stale sources'
    assert db.audit_events.count_documents({'action':'requirement.rules'})==1
    assert client.get('/verification?role_id=role').status_code==200
    token=login(client,'employee')
    assert client.post(path,data=annotate_data(token)).status_code==403


def test_structured_values_conditions_exceptions_and_answers_are_checked():
    quote='During a shift, acknowledge within 2 hours. Except urgent incidents.'
    req={'_id':'r','requirement_id':'R1','document_id':'d','section_id':'s','text':quote,'mandatory':True,
         'status':'approved','role_ids':['role'],'due_stage':'Week 1','prerequisites':[],
         'policy_rule':{'key':'ack.hours','value':'2 hours','condition':'During a shift','exception':'Except urgent incidents.',
                        'answer_fact':'2 hours','module_category':'Communication','assessment_topic':'Acknowledgement'}}
    item=full_item({'requirement_id':'R1','source_document_id':'d','source_section_id':'s','text':quote,'mandatory':True})
    item.update(policy_facts=deepcopy(req['policy_rule']),lesson='Apply the approved acknowledgement rule. During a shift, respond promptly. Except urgent incidents.')
    item['quiz']['options'][0]='2 hours'
    def validate(item):
        return validate_plan(FullOnboardingPlan(title='Test',summary='Test',role_id='role',items=[item]),[req],
            [{'_id':'d','status':'active'}],[{'document_id':'d','section_id':'s','text':quote}],'role')
    assert validate(item)['core_passed']
    item['policy_facts']['value']='24 hours';item['lesson']='This lesson deliberately omits the reviewed condition and exception.'
    item['quiz']['correct_index']=1
    codes={f['code'] for f in validate(item)['findings']}
    assert {'STRUCTURED_RULE_MISMATCH','CONDITION_OMITTED','EXCEPTION_OMITTED','QUIZ_ANSWER_FACT_MISMATCH'}<=codes


def test_conflict_precedence_is_explicit_and_expires_on_rule_change(training):
    client,db,settings,plan,token=training
    req=db.requirements.find_one({});client.post('/requirements/'+req['_id']+'/rules',data=annotate_data(token))
    upload_docx(client,token,'Employees must leave their workstations unlocked.',document_id='CONFLICT-01')
    doc=db.documents.find_one({'document_id':'CONFLICT-01'});approve(client,db,token,doc)
    other=db.requirements.find_one({'document_id':doc['_id']})
    assert client.post('/requirements/'+other['_id']+'/rules',data=annotate_data(token,value='unlocked',answer_fact='unlocked')).status_code==200
    state=matrix_state(db,'role');assert len(state['unresolved'])==1
    job=enqueue(db,'admin','generate','learner');process_one(db,settings,provider)
    assert db.jobs.find_one({'_id':job['_id']})['status']=='failed'
    conflict=state['conflicts'][0]
    response=client.post('/verification/role/resolve',data={'csrf_token':token,'conflict_id':conflict['_id'],
        'winner_id':req['requirement_id'],'reason':'The reviewed security policy takes precedence over this contradictory test FAQ.'})
    assert response.status_code==200
    state=matrix_state(db,'role');assert not state['unresolved'] and len(state['requirements'])==1
    assert state['excluded']==[other['requirement_id']]
    db.requirements.update_one({'_id':other['_id']},{'$set':{'policy_rule.exception':'workstations'}})
    assert len(matrix_state(db,'role')['unresolved'])==1
    assert client.post('/verification/role/resolve',data={'csrf_token':token,'conflict_id':conflict['_id'],
        'winner_id':req['requirement_id'],'reason':'Stale form'}).status_code==409


def test_prerequisite_cycles_and_unavailable_dependencies():
    findings=dependency_findings([{'requirement_id':'A','prerequisites':['B']},{'requirement_id':'B','prerequisites':['A','missing']}])
    assert {'PREREQUISITE_CYCLE','PREREQUISITE_UNAVAILABLE'} <= {f['code'] for f in findings}


@pytest.fixture
def revision(training):
    client,db,settings,_,token=training
    first=db.documents.find_one({})
    upload_docx(client,token,'Employees must use multifactor authentication.',document_id='MFA-01')
    second=db.documents.find_one({'document_id':'MFA-01'});approve(client,db,token,second)
    job=enqueue(db,'admin','generate','learner');process_one(db,settings,provider)
    base=db.plans.find_one({'_id':job['_id']});assert publish(client,base,token).status_code==200
    keep=next(i for i in base['content']['items'] if i['source_document_id']==first['_id'])
    change=next(i for i in base['content']['items'] if i['source_document_id']==second['_id'])
    # Explicit seeded test history: verify migration of both partial and passed work.
    for item in (keep,change):
        identity={'plan_id':base['_id'],'employee_id':'learner','requirement_id':item['requirement_id']}
        db.learning_progress.insert_one({'_id':'progress-'+item['requirement_id'],**identity,'checked':[0,1],'lesson_read':True})
        db.quiz_attempts.insert_one({'_id':'quiz-'+item['requirement_id'],**identity,'answer':0,'score':100,'passed':True,'feedback':'Test-only feedback','created_at':now()})
        db.practical_submissions.insert_one({'_id':'submission-'+item['requirement_id'],**identity,'status':'graded','percent':100,'passed':True,
            'scores':[5,5],'maximum':10,'feedback':'Synthetic prior test assessment','scenario_response':'Test scenario','practical_response':'Test evidence','created_at':now()})
    upload_docx(client,token,'Employees must use multifactor authentication and keep recovery codes private.',document_id='MFA-01',version='2.0',effective='2026-02-01')
    replacement=db.documents.find_one({'document_id':'MFA-01','version':'2.0'})
    yield client,db,settings,base,token,keep,change,replacement


def test_policy_preview_and_selective_regeneration_carry_only_unchanged_work(revision):
    client,db,settings,base,token,keep,change,replacement=revision
    response=client.get('/documents/'+replacement['_id']+'/impact')
    assert response.status_code==200 and 'Test Learner' in response.text and '1 modules' in response.text
    approve(client,db,token,replacement)
    assert client.get('/plans/'+base['_id']+'/update').status_code==200
    delta=selective_delta(base,matrix(db,'role'));assert delta['retained']==[keep['requirement_id']]
    assert delta['removed']==[change['requirement_id']]
    calls=[]
    def tracked(*args):
        calls.extend(r['requirement_id'] for r in args[3]['requirements']);return provider(*args)
    response=client.post('/plans/'+base['_id']+'/update',data={'csrf_token':token});assert response.status_code==200
    process_one(db,settings,tracked)
    new=db.plans.find_one({'origin':'selective_update'})
    assert new and calls==delta['regenerate'] and new['validation']['core_passed']
    assert db.learning_progress.count_documents({'plan_id':new['_id']})==0
    assert publish(client,new,token).status_code==200
    for name in ['learning_progress','quiz_attempts','practical_submissions']:
        copied=list(db[name].find({'plan_id':new['_id']}));assert len(copied)==1
        assert copied[0]['requirement_id']==keep['requirement_id'] and copied[0]['carried_from_plan_id']==base['_id']
        assert db[name].count_documents({'plan_id':base['_id']})==2
    assert db.plans.find_one({'_id':base['_id']})['content']==base['content']
    assert client.get('/plans/'+base['_id']+'/compare?other='+new['_id']).status_code==200
    token=login(client,'employee');response=client.get('/learning/'+new['_id'])
    assert response.status_code==200 and '50%' in response.text
    assert client.post('/learning/'+base['_id']+'/'+keep['requirement_id']+'/quiz',data={'csrf_token':token,'answer':0}).status_code==409


def test_selective_update_invalidates_dependents_and_never_copies_edited_modules(revision):
    client,db,settings,base,token,keep,change,replacement=revision
    new_reqs=deepcopy(base['matrix_snapshot'])
    dep=next(r for r in new_reqs if r['requirement_id']==keep['requirement_id']);dep['prerequisites']=[change['requirement_id']]
    original=deepcopy(base);original['matrix_snapshot']=deepcopy(new_reqs)
    next(r for r in new_reqs if r['requirement_id']==change['requirement_id'])['text']='Changed obligation.'
    assert not selective_delta(original,new_reqs)['retained']
    approve(client,db,token,replacement)
    job=enqueue(db,'admin','selective','learner',base_plan_id=base['_id']);process_one(db,settings,provider)
    new=db.plans.find_one({'_id':job['_id']});item=next(i for i in new['content']['items'] if i['requirement_id']==keep['requirement_id'])
    form=edit_form(item,token);form['module_title']='A manually changed retained module'
    assert client.post('/plans/'+new['_id']+'/items/'+keep['requirement_id']+'/edit',data=form).status_code==200
    edited=db.plans.find_one({'parent_plan_id':new['_id']})
    assert publish(client,edited,token).status_code==200
    assert db.learning_progress.count_documents({'plan_id':edited['_id']})==0


def test_two_controlled_runs_and_exports_are_reproducible(training):
    client,db,settings,plan,token=training
    response=client.post('/plans/'+plan['_id']+'/consistency',data={'csrf_token':token});assert response.status_code==200
    experiment=db.consistency_experiments.find_one({})
    process_one(db,settings,provider);process_one(db,settings,provider)
    response=client.get('/experiments/'+experiment['_id']);assert response.status_code==200 and '100.0%' in response.text
    result=client.get('/experiments/'+experiment['_id']+'/json').json()
    assert result['comparison']['comparable'] and result['comparison']['consistency_score']==100
    assert db.consistency_experiments.find_one({})['result']['consistency_score']==100
    plans=list(db.plans.find({'experiment_id':experiment['_id']}))
    altered=deepcopy(plans[1]);altered['snapshot_digest']='different'
    assert compare_plans(plans[0],altered)['consistency_score'] is None


def test_controlled_run_fails_when_inputs_change(training):
    client,db,settings,plan,token=training
    client.post('/plans/'+plan['_id']+'/consistency',data={'csrf_token':token})
    db.employees.update_one({'_id':'learner'},{'$set':{'experience':'Advanced'}})
    process_one(db,settings,provider)
    assert db.jobs.find_one({'experiment_id':{'$ne':None},'status':'failed'})


def test_reports_filters_csv_safety_and_access_scoping(training):
    client,db,_,plan,token=training
    db.employees.update_one({'_id':'learner'},{'$set':{'name':'=HYPERLINK("unsafe")'}})
    assert client.get('/reports?q=HYPERLINK&role_id=role').status_code==200
    csv_text=client.get('/reports.csv?q=HYPERLINK').text.lstrip('\ufeff')
    rows=list(csv.reader(io.StringIO(csv_text)));assert len(rows)==2 and rows[1][0].startswith("'=")
    assert len(list(csv.reader(io.StringIO(client.get('/reports.csv?q=absent').text))))==1
    assert client.get('/plans/'+plan['_id']+'/validation.csv').status_code==200
    login(client,'employee');assert client.get('/reports').status_code==200
    assert client.get('/verification').status_code==403
    db.employees.update_one({'_id':'learner'},{'$set':{'user_id':'another'}})
    assert client.get('/plans/'+plan['_id']+'/validation.csv').status_code==404
    assert 'HYPERLINK' not in client.get('/reports.csv').text


def test_publication_and_learning_writes_obey_employee_lock(training):
    client,db,_,plan,token=training
    db.employees.update_one({'_id':'learner'},{'$set':{'write_lock':{'owner':'other','expires_at':now()+timedelta(minutes=1)}}})
    assert publish(client,plan,token).status_code==409
    db.employees.update_one({'_id':'learner'},{'$set':{'write_lock.expires_at':now()-timedelta(minutes=1)}})
    assert publish(client,plan,token).status_code==200
    assert 'write_lock' not in db.employees.find_one({'_id':'learner'})


@pytest.mark.parametrize('repair_result',['valid','invalid','outage'])
def test_bounded_repair_preserves_original_and_blocks_unfixed_output(training,repair_result):
    from app.generation import GenerationFailure
    client,db,settings,_,token=training
    req=db.requirements.find_one({})
    assert client.post('/requirements/'+req['_id']+'/rules',data=annotate_data(token)).status_code==200
    calls=[]
    def repair_provider(settings,schema,template,payload,on_attempt):
        calls.append(payload)
        if len(calls)==2 and repair_result=='outage':
            raise GenerationFailure('Synthetic provider outage')
        result,metadata=provider(settings,schema,template,payload,on_attempt)
        if len(calls)==1 or repair_result=='invalid':
            result.items[0].quiz.options[0]='Unsupported answer'
        return result,metadata
    job=enqueue(db,'admin','generate','learner');process_one(db,settings,repair_provider)
    saved=db.jobs.find_one({'_id':job['_id']})
    assert len(calls)==2
    assert saved['repair_evidence']['content']['items'][0]['quiz']['options'][0]=='Unsupported answer'
    if repair_result=='outage':
        assert saved['status']=='failed'
        assert not db.plans.find_one({'_id':job['_id']})
    else:
        plan=db.plans.find_one({'_id':job['_id']})
        assert plan['validation']['core_passed']==(repair_result=='valid')
        assert plan['generation']['pre_repair_content']==saved['repair_evidence']['content']
        assert publish(client,plan,token).status_code==(200 if repair_result=='valid' else 409)
