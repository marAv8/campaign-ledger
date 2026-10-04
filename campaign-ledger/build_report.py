"""Validated CSV -> SQLite -> SQL metrics -> portable dashboard. Standard library only."""
import csv,json,sqlite3
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TABLES={
 'campaigns':['campaign_id','name','channel'],
 'daily_spend':['campaign_id','day','ad_spend_cents','other_acquisition_cents','impressions','clicks'],
 'customers':['customer_id','campaign_id','acquired_day'],
 'orders':['order_id','customer_id','campaign_id','day','revenue_cents']}
NUMERIC={'ad_spend_cents','other_acquisition_cents','impressions','clicks','revenue_cents'}

def connect(path):
 db=sqlite3.connect(path);db.row_factory=sqlite3.Row
 db.executescript((ROOT/'sql/schema.sql').read_text());return db

def import_data(db,folder):
 # Validate all source rows before a single atomic replacement of the snapshot.
 data={}
 for table,fields in TABLES.items():
  with (folder/f'{table}.csv').open(newline='') as f:
   reader=csv.DictReader(f)
   if reader.fieldnames!=fields:raise ValueError(f'{table}: unexpected columns')
   rows=[]
   for row in reader:
    if None in row or any(v is None or not v.strip() for v in row.values()):raise ValueError(f'{table}: incomplete row')
    for key in fields:
     if key in NUMERIC:row[key]=int(row[key])
     elif key in {'day','acquired_day'}:
      if date.fromisoformat(row[key]).isoformat()!=row[key]:raise ValueError('Dates must be YYYY-MM-DD')
    rows.append(tuple(row[k] for k in fields))
   data[table]=rows
 with db:
  for table in reversed(TABLES):db.execute(f'DELETE FROM {table}')
  for table,fields in TABLES.items():
   db.executemany(f'INSERT INTO {table} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})',data[table])
  invalid=db.execute('SELECT COUNT(*) FROM orders o JOIN customers c USING(customer_id) WHERE o.day<c.acquired_day OR o.campaign_id!=c.campaign_id').fetchone()[0]
  if invalid:raise ValueError('Order attribution or acquisition date is inconsistent')

def metrics(db,start,end):
 return [dict(row) for row in db.execute((ROOT/'sql/campaign_metrics.sql').read_text(),{'start':start,'end':end})]

def report(db):
 start,end=db.execute('SELECT MIN(day),MAX(day) FROM daily_spend').fetchone()
 if start is None:raise ValueError('No daily campaign data to report')
 last=date.fromisoformat(end);current_start=str(last-timedelta(days=6));previous_end=str(last-timedelta(days=7));previous_start=str(last-timedelta(days=13))
 windows={'all':{'label':'All 14 sample days','start':start,'end':end},'current':{'label':'Latest 7 sample days','start':current_start,'end':end},'previous':{'label':'Previous 7 sample days','start':previous_start,'end':previous_end}}
 for w in windows.values():w['rows']=metrics(db,w['start'],w['end'])
 previous={r['campaign_id']:r for r in windows['previous']['rows']};alerts=[]
 for r in windows['current']['rows']:
  p=previous[r['campaign_id']]
  if p['ad_spend_cents']>0 and r['ad_spend_cents']>=p['ad_spend_cents']*1.25:
   alerts.append({'campaign_id':r['campaign_id'],'channel':r['channel'],'name':r['name'],'message':f"Ad spend rose {(r['ad_spend_cents']/p['ad_spend_cents']-1)*100:.0f}% versus the previous 7 days.",'rule':'spend increase ≥25%'})
  if p['roas'] is not None and p['roas']>0 and r['roas'] is not None and r['roas']<=p['roas']*.75:
   alerts.append({'campaign_id':r['campaign_id'],'channel':r['channel'],'name':r['name'],'message':f"ROAS fell from {p['roas']:.2f}× to {r['roas']:.2f}× versus the previous 7 days.",'rule':'ROAS decline ≥25%'})
 return {'windows':windows,'alerts':alerts,'data_kind':'fictional sample data','currency':'USD','generated_from':'SQLite SQL queries','attribution':'Each sample customer and order is assigned to one campaign; no overlapping channel attribution.'}

def build():
 out=ROOT/'output';out.mkdir(exist_ok=True)
 db=connect(out/'campaigns.sqlite')
 try:import_data(db,ROOT/'data');payload=report(db)
 finally:db.close()
 (out/'metrics.json').write_text(json.dumps(payload,indent=2))
 encoded=json.dumps(payload).replace('<','\\u003c')
 (out/'index.html').write_text((ROOT/'dashboard.html').read_text().replace('__REPORT_JSON__',encoded))
 print('Built output/index.html, output/metrics.json, and output/campaigns.sqlite')
if __name__=='__main__':build()
