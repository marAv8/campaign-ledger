import copy,io,json,os,threading,unittest
from unittest.mock import patch
from build_report import connect
from workflow import run,stage,snapshot
from mock_sources import fixtures,server
from claude_brief import create_brief,validate

class WorkflowTests(unittest.TestCase):
 def setUp(self):self.db=connect(':memory:')
 def tearDown(self):self.db.close()
 def execute(self,scenario):
  service=server(scenario);thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
  try:return run(self.db,f'http://127.0.0.1:{service.server_port}')
  finally:service.shutdown();service.server_close();thread.join()
 def test_http_failure_preserves_report_and_logs_failure(self):
  good=self.execute('success');bad=self.execute('failure')
  self.assertEqual(good['report'],bad['report']);self.assertEqual(bad['status'],'failed');self.assertIn('google',bad['detail']);self.assertEqual(len(bad['history']),2)
 def test_correction_changes_totals_once(self):
  before=self.execute('success');corrected=self.execute('correction');repeated=self.execute('correction')
  total=lambda r,k:sum(x[k] for x in r['report']['windows']['all']['rows'])
  self.assertEqual(total(corrected,'ad_spend_cents')-total(before,'ad_spend_cents'),5000)
  self.assertEqual(corrected['report'],repeated['report']);self.assertNotEqual(before['fingerprint'],corrected['fingerprint'])
  self.assertEqual(total(corrected,'net_revenue_cents'),total(corrected,'revenue_cents')-total(corrected,'refund_cents'))
 def test_incomplete_or_stale_source_rejected(self):
  for kind in ('incomplete','stale','missing_day'):
   p=fixtures()
   if kind=='incomplete':p['google']['complete']=False
   elif kind=='stale':p['google']['refreshed_at']='2026-10-01T08:30:00+00:00'
   else:p['google']['tables']['daily_spend'].pop();p['google']['row_counts']['daily_spend']-=1
   with self.assertRaises(ValueError):stage(p)
 def test_excessive_refund_rejected(self):
  p=fixtures();p['store']['tables']['refunds'][0]['amount_cents']=99999999
  with self.assertRaises(ValueError):stage(p)
 def test_claude_adapter_validates_response_and_falls_back(self):
  staging=stage(fixtures());p=snapshot(staging);staging.close();r=p['windows']['current']['rows'][0]
  fact={'campaign_id':r['campaign_id'],'metric':'net_roas','value':r['net_roas']}
  good={'facts':[fact],'questions':['Check tracking coverage before changing spending.']}
  opener=lambda *args,**kwargs:io.BytesIO(json.dumps({'content':[{'type':'text','text':json.dumps(good)}]}).encode())
  with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'test-only','ANTHROPIC_MODEL':'test-model'}):
   self.assertEqual(create_brief(p,opener)['status'],'validated')
   good['facts'][0]['value']=9999
   self.assertEqual(create_brief(p,opener)['status'],'fallback')
 def test_claude_missing_configuration_does_not_call_api(self):
  staging=stage(fixtures());p=snapshot(staging);staging.close()
  with patch.dict(os.environ,{},clear=True):
   self.assertEqual(create_brief(p,lambda *a,**k:self.fail('Unexpected external request'))['status'],'not_configured')
if __name__=='__main__':unittest.main()
