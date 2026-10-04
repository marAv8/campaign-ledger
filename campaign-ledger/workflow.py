"""HTTP source adapters -> validated snapshot -> SQLite -> review payload.

The adapter contract is our fictional API, not Meta/Google's real API.
Run history persists even when a refresh fails; the last valid snapshot survives.
"""
import argparse, csv, hashlib, io, json, os, sqlite3, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from build_report import ROOT, TABLES, connect, import_data, report

AS_OF='2026-10-03T09:00:00+00:00'
REFUNDS=['refund_id','order_id','day','amount_cents']

def fetch(base, source, attempts=3):
 for attempt in range(attempts):
  try:
   with urlopen(base.rstrip('/')+'/'+source,timeout=5) as response:
    return json.load(response)
  except (HTTPError, URLError, TimeoutError):
   if attempt+1==attempts:raise ValueError(source+': unavailable after 3 attempts') from None
   time.sleep(.05*(2**attempt))

def initialize(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS refunds(
 refund_id TEXT PRIMARY KEY,order_id TEXT NOT NULL REFERENCES orders(order_id),
 day TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>=0));
 CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,status TEXT NOT NULL,
 attempted_at TEXT NOT NULL,detail TEXT NOT NULL,fingerprint TEXT);''')

def stage(envelopes):
 data={k:[] for k in TABLES};refunds=[]
 for source,p in envelopes.items():
  if p.get('currency')!='USD' or p.get('complete') is not True:
   raise ValueError(source+': incomplete snapshot or unsupported currency')
  refreshed=datetime.fromisoformat(p['refreshed_at']);now=datetime.fromisoformat(AS_OF)
  if refreshed.tzinfo is None or not 0 <= (now-refreshed).total_seconds() <= 86400:
   raise ValueError(source+': stale or invalid source timestamp')
  if p.get('window')!=['2026-09-19','2026-10-02']:raise ValueError(source+': incompatible reporting window')
  expected_tables={'campaigns','daily_spend'} if source in ('meta','google') else {'customers','orders','refunds'}
  if set(p['tables'])!=expected_tables:raise ValueError(source+': unexpected tables')
  for table,rows in p['tables'].items():
   if p['row_counts'].get(table)!=len(rows):raise ValueError(source+': record count mismatch')
   if table=='refunds':refunds=rows
   else:data[table].extend(rows)
  if source in ('meta','google'):
   ids={r['campaign_id'] for r in p['tables']['campaigns']}
   if any(r['channel']!=source.title() for r in p['tables']['campaigns']) or any(r['campaign_id'] not in ids for r in p['tables']['daily_spend']):
    raise ValueError(source+': channel mismatch')
 staging=connect(':memory:');initialize(staging)
 try:
  with tempfile.TemporaryDirectory() as td:
   for table,fields in TABLES.items():
    with (Path(td)/(table+'.csv')).open('w',newline='') as f:
     writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(data[table])
   import_data(staging,Path(td))
  # Every campaign requires each day in the declared full snapshot.
  bad=staging.execute('SELECT c.campaign_id FROM campaigns c LEFT JOIN daily_spend d USING(campaign_id) GROUP BY c.campaign_id HAVING COUNT(d.day)!=14 OR MIN(d.day)!=? OR MAX(d.day)!=?',('2026-09-19','2026-10-02')).fetchall()
  if bad or not data['campaigns']:raise ValueError('Missing campaign days in full snapshot')
  with staging:
   for r in refunds:
    if set(r)!=set(REFUNDS):raise ValueError('Unexpected refund fields')
    datetime.strptime(r['day'],'%Y-%m-%d')
    if type(r['amount_cents']) is not int:raise ValueError('Refund amount must be integer cents')
    staging.execute('INSERT INTO refunds VALUES(?,?,?,?)',tuple(r[k] for k in REFUNDS))
   bad=staging.execute('SELECT o.order_id FROM orders o JOIN refunds r USING(order_id) GROUP BY o.order_id HAVING SUM(r.amount_cents)>o.revenue_cents OR MIN(r.day)<o.day OR MAX(r.day)>?',('2026-10-02',)).fetchall()
   if bad:raise ValueError('Refund exceeds order value or has inconsistent date')
  return staging
 except Exception:
  staging.close();raise

def snapshot(db):
 payload=report(db)
 for w in payload['windows'].values():
  refund_totals={r[0]:r[1] for r in db.execute('SELECT o.campaign_id,SUM(r.amount_cents) FROM refunds r JOIN orders o USING(order_id) WHERE r.day BETWEEN ? AND ? GROUP BY o.campaign_id',(w['start'],w['end']))}
  for row in w['rows']:
   row['refund_cents']=refund_totals.get(row['campaign_id'],0)
   row['net_revenue_cents']=row['revenue_cents']-row['refund_cents']
   row['net_roas']=row['net_revenue_cents']/row['ad_spend_cents'] if row['ad_spend_cents'] else None
 w=payload['windows']['all']
 payload['audiences']=[dict(r) for r in db.execute((ROOT/'sql/audiences.sql').read_text(),{'start':w['start'],'end':w['end']})]
 return payload

def run(db,base,as_of=AS_OF):
 initialize(db);sources=[];staging=None
 try:
  envelopes={}
  for source in ('meta','google','store'):
   envelopes[source]=fetch(base,source)
   sources.append({'source':source,'status':'received','refreshed_at':envelopes[source]['refreshed_at'],'records':sum(envelopes[source]['row_counts'].values())})
  staging=stage(envelopes)
  fingerprint=hashlib.sha256(json.dumps(envelopes,sort_keys=True).encode()).hexdigest()
  with db:
   for table in ('refunds','orders','customers','daily_spend','campaigns'):db.execute('DELETE FROM '+table)
   for table,fields in {**TABLES,'refunds':REFUNDS}.items():
    rows=staging.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall()
    db.executemany('INSERT INTO '+table+' VALUES('+','.join('?' for _ in fields)+')',[tuple(r) for r in rows])
   db.execute('INSERT INTO runs(status,attempted_at,detail,fingerprint) VALUES(?,?,?,?)',('success',as_of,'All sources validated; snapshot published',fingerprint))
  outcome={'status':'success','detail':'All sources validated. Report ready.','sources':sources,'fingerprint':fingerprint}
 except (ValueError,KeyError,TypeError,sqlite3.Error) as e:
  with db:db.execute('INSERT INTO runs(status,attempted_at,detail) VALUES(?,?,?)',('failed',as_of,str(e)))
  outcome={'status':'failed','detail':str(e),'sources':sources}
 finally:
  if staging:staging.close()
 previous=db.execute("SELECT attempted_at FROM runs WHERE status='success' ORDER BY id DESC LIMIT 1").fetchone()
 outcome['last_success']=previous[0] if previous else None
 outcome['attempted_at']=as_of
 outcome['report']=snapshot(db) if db.execute('SELECT COUNT(*) FROM daily_spend').fetchone()[0] else None
 outcome['history']=[dict(r) for r in db.execute('SELECT id,status,attempted_at,detail FROM runs ORDER BY id DESC LIMIT 5')]
 return outcome

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--db',default=str(ROOT/'output/workflow.sqlite'));parser.add_argument('--claude',action='store_true');args=parser.parse_args()
 db=connect(args.db)
 try:payload=run(db,args.base_url)
 finally:db.close()
 if args.claude and payload['status']=='success' and payload['report']:
  from claude_brief import create_brief
  payload['ai_review']=create_brief(payload['report'])
 (ROOT/'output/workflow.json').write_text(json.dumps(payload,indent=2))
 print(payload['status']+': '+payload['detail'])
 return 0 if payload['status']=='success' else 1
if __name__=='__main__':raise SystemExit(main())
