"""Local management commands. Credentials are never printed."""
import argparse
import json
from pathlib import Path
from app.config import Settings, ROOT
from app.db import connect, initialize, now, uid, audit
from app.security import hash_password
from app.ingestion import ingest


def main():
    parser=argparse.ArgumentParser(description='SkillSprint local setup')
    parser.add_argument('command',choices=['init','check'])
    parser.add_argument('--seed-company',action='store_true',help='Import AsterBridge documents as drafts; never approve requirements automatically.')
    args=parser.parse_args()
    settings=Settings(); client,db=connect(settings)
    try:
        if args.command=='check':
            print(json.dumps({'mongodb':'connected','database':settings.mongodb_db_name,
                'ai_key_configured':bool(settings.openai_api_key),'model':settings.genai_model,
                'users':db.users.count_documents({}),'documents':db.documents.count_documents({})}))
            return
        initialize(db)
        email=settings.bootstrap_admin_email.strip().lower()
        admin=db.users.find_one({'email':email})
        if not admin:
            if len(settings.bootstrap_admin_password)<12:
                raise SystemExit('Set BOOTSTRAP_ADMIN_PASSWORD in .env to at least 12 characters before initializing.')
            admin={'_id':uid(),'name':'Workspace Admin','email':email,'password_hash':hash_password(settings.bootstrap_admin_password),
                'role':'admin','active':True,'created_at':now()}
            db.users.insert_one(admin)
            audit(db,admin['_id'],'workspace.initialize',admin['_id'])
        if args.seed_company:
            pack=ROOT/'sample_documents'/'asterbridge'
            roles=json.loads((pack/'reference/roles.json').read_text(encoding='utf-8'))
            for role in roles:
                db.job_roles.update_one({'_id':role['role_id']},{'$setOnInsert':{'name':role['title'],'department':role['department'],
                    'description':role['purpose'],'created_at':now()}},upsert=True)
            register=json.loads((pack/'reference/document_register.json').read_text(encoding='utf-8'))
            imported=0
            for doc in register:
                if doc['status']!='approved' or db.documents.find_one({'document_id':doc['document_id'],'version':doc['version']}):
                    continue
                path=pack/doc['source_path']
                ingest(db,settings,path.read_bytes(),path.name,{'document_id':doc['document_id'],'version':doc['version'],
                    'title':doc['title'],'effective_date':doc['effective_from'],'category':doc['category'],
                    'role_ids':doc['role_ids'] if len(doc['role_ids'])==1 else []},admin['_id'])
                imported+=1
            if not db.employees.find_one({'seed_id':'amina-demo'}):
                db.employees.insert_one({'_id':uid(),'seed_id':'amina-demo','name':'Amina Hassan (demo)', 'role_id':'CS',
                    'role_name':'Customer Support Executive','department':'Customer Experience','experience':'Beginner',
                    'joining_date':str(now().date()),'manager_id':admin['_id'],'user_id':'','created_at':now()})
            print(f'Imported {imported} documents as drafts. No requirements were automatically approved.')
        print(f'Workspace initialized. Administrator: {email}. Password is the local BOOTSTRAP_ADMIN_PASSWORD value in .env.')
    finally:
        client.close()


if __name__=='__main__':
    main()
