"""Progress migration is limited to byte-equivalent, unchanged learning modules."""
from copy import deepcopy
from datetime import timedelta
from functools import wraps
import hashlib
import inspect
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from .db import now, uid
from .schemas import FullLearningItem
from .policy import selective_delta
from .security import require, can_read_employee


def serialized_learning(function):
    """Serialize publication and learner writes per employee, including across workers."""
    @wraps(function)
    async def wrapped(*args, **kwargs):
        request = kwargs.get('request') or args[0]
        user, _ = require(request)
        db = request.app.state.db
        plan_id = kwargs.get('plan_id')
        if not plan_id:
            submission = db.practical_submissions.find_one({'_id':kwargs.get('submission_id')})
            plan_id = submission['plan_id'] if submission else None
        plan = db.plans.find_one({'_id':plan_id})
        employee = db.employees.find_one({'_id':plan['employee_id']}) if plan else None
        if not employee or not can_read_employee(user,employee):
            raise HTTPException(404,'Learning record not found.')
        owner = uid()
        locked = db.employees.update_one({'_id':employee['_id'], '$or':[
            {'write_lock':{'$exists':False}}, {'write_lock.expires_at':{'$lt':now()}}]},
            {'$set':{'write_lock':{'owner':owner,'expires_at':now()+timedelta(minutes=3)}}})
        if not locked.matched_count:
            raise HTTPException(409,'Another learning update is being saved. Please retry shortly.')
        try:
            if inspect.iscoroutinefunction(function): return await function(*args,**kwargs)
            return await run_in_threadpool(function,*args,**kwargs)
        finally:
            db.employees.update_one({'_id':employee['_id'],'write_lock.owner':owner},{'$unset':{'write_lock':''}})
    return wrapped


def carry_progress(db, plan, employee):
    if plan.get('origin')!='selective_update' and not plan.get('carry_parent_plan_id'): return {}
    parent = db.plans.find_one({'_id':plan.get('carry_parent_plan_id') or plan.get('parent_plan_id'),'employee_id':employee['_id']})
    if not parent or employee.get('active_plan_id')!=parent['_id'] or not parent.get('published_at'):
        raise HTTPException(409,'The assigned plan changed. Start a new selective update to preserve the latest learning history.')
    eligible = set(selective_delta(parent,plan['matrix_snapshot'],plan.get('employee_snapshot'))['retained'])
    old = {i['requirement_id']:i for i in parent['content']['items']}
    new = {i['requirement_id']:i for i in plan['content']['items']}
    eligible = {key for key in eligible if key in new and
        FullLearningItem.model_validate(old[key]).model_dump()==FullLearningItem.model_validate(new[key]).model_dump()}
    counts = {}
    for name in ('learning_progress','quiz_attempts','practical_submissions'):
        collection = db[name]; copied=0
        for row in collection.find({'plan_id':parent['_id'],'employee_id':employee['_id'],'requirement_id':{'$in':list(eligible)}}):
            record = deepcopy(row)
            record.update(_id=hashlib.sha256((plan['_id']+name+row['_id']).encode()).hexdigest(), plan_id=plan['_id'],
                          carried_from_plan_id=parent['_id'],carried_from_record_id=row['_id'],carried_at=now())
            result=collection.update_one({'_id':record['_id']},{'$setOnInsert':record},upsert=True)
            copied += int(result.upserted_id is not None)
        counts[name]=copied
    db.plans.update_one({'_id':plan['_id']},{'$set':{'progress_carry':{'parent_plan_id':parent['_id'],
        'requirement_ids':sorted(eligible),'counts':counts,'at':now()}}})
    return counts
