"""Local HTTP simulator for three separate fictional source contracts."""
import copy,csv,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from build_report import ROOT,NUMERIC

def fixtures(scenario='success'):
 tables={}
 for name in ('campaigns','daily_spend','customers','orders'):
  with (ROOT/'data'/f'{name}.csv').open() as f:tables[name]=list(csv.DictReader(f))
  for row in tables[name]:
   for k in row:
    if k in NUMERIC:row[k]=int(row[k])
 order=tables['orders'][0]
 tables['refunds']=[{'refund_id':'refund_sample_1','order_id':order['order_id'],'day':'2026-10-02','amount_cents':min(2500,order['revenue_cents'])}]
 if scenario=='correction':
  row=next(r for r in tables['daily_spend'] if r['campaign_id']=='meta_prospect' and r['day']=='2026-10-02')
  row['ad_spend_cents']+=5000
  tables['refunds'][0]['amount_cents']+=min(1500,order['revenue_cents']-tables['refunds'][0]['amount_cents'])
 result={}
 for source in ('meta','google','store'):
  if source=='store':selected={k:tables[k] for k in ('customers','orders','refunds')}
  else:
   ids={r['campaign_id'] for r in tables['campaigns'] if r['channel']==source.title()}
   selected={k:[r for r in tables[k] if r['campaign_id'] in ids] for k in ('campaigns','daily_spend')}
  result[source]={'currency':'USD','complete':True,'refreshed_at':'2026-10-03T08:30:00+00:00','window':['2026-09-19','2026-10-02'],'tables':selected,'row_counts':{k:len(v) for k,v in selected.items()}}
 return result

def server(scenario='success',port=0):
 payload=fixtures('correction' if scenario=='correction' else 'success')
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   name=self.path.strip('/')
   if scenario=='failure' and name=='google':self.send_error(503,'Simulated outage');return
   if name not in payload:self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(payload[name]).encode())
  def log_message(self,*args):pass
 return ThreadingHTTPServer(('127.0.0.1',port),Handler)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['success','failure','correction'],default='success');p.add_argument('--port',type=int,default=8765);a=p.parse_args()
 s=server(a.scenario,a.port);print(f'Fictional source APIs listening on localhost:{s.server_port}',flush=True);s.serve_forever()
