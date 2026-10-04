import csv,json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from build_report import ROOT,connect,import_data,metrics,report

class ReportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)/'data';shutil.copytree(ROOT/'data',self.folder)
  self.db=connect(':memory:');import_data(self.db,self.folder)
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def test_aggregate_joins_do_not_multiply_money(self):
  rows=metrics(self.db,'2026-09-19','2026-10-02')
  self.assertEqual(sum(r['ad_spend_cents'] for r in rows),self.db.execute('SELECT SUM(ad_spend_cents) FROM daily_spend').fetchone()[0])
  self.assertEqual(sum(r['revenue_cents'] for r in rows),self.db.execute('SELECT SUM(revenue_cents) FROM orders').fetchone()[0])
  self.assertEqual(sum(r['new_customers'] for r in rows),self.db.execute('SELECT COUNT(*) FROM customers').fetchone()[0])
 def test_cac_and_roas_use_correct_denominators(self):
  for r in metrics(self.db,'2026-09-19','2026-10-02'):
   self.assertAlmostEqual(r['cac'],(r['ad_spend_cents']+r['other_acquisition_cents'])/100/r['new_customers'])
   self.assertAlmostEqual(r['roas'],r['revenue_cents']/r['ad_spend_cents'])
 def test_repeat_import_is_idempotent(self):
  before=report(self.db);import_data(self.db,self.folder);self.assertEqual(report(self.db),before)
 def test_invalid_foreign_key_rolls_back_existing_snapshot(self):
  before=report(self.db)
  with (self.folder/'orders.csv').open('a') as f:f.write('\ninvalid_order,missing_customer,meta_prospect,2026-10-02,100\n')
  with self.assertRaises(sqlite3.IntegrityError):import_data(self.db,self.folder)
  self.assertEqual(report(self.db),before)
 def test_duplicate_daily_record_is_rejected_atomically(self):
  before=report(self.db);lines=(self.folder/'daily_spend.csv').read_text().splitlines()
  with (self.folder/'daily_spend.csv').open('a') as f:f.write(lines[1]+'\n')
  with self.assertRaises(sqlite3.IntegrityError):import_data(self.db,self.folder)
  self.assertEqual(report(self.db),before)
 def test_zero_denominators_are_unavailable(self):
  for r in metrics(self.db,'2030-01-01','2030-01-02'):
   self.assertIsNone(r['cac']);self.assertIsNone(r['roas'])
 def test_alerts_detect_known_change_not_every_campaign(self):
  alerts=report(self.db)['alerts'];self.assertTrue(any(a['rule']=='spend increase ≥25%' for a in alerts));self.assertTrue(any(a['rule']=='ROAS decline ≥25%' for a in alerts));self.assertTrue(all(a['campaign_id']=='meta_prospect' for a in alerts))
 def test_mismatched_campaign_is_rejected(self):
  before=report(self.db);path=self.folder/'orders.csv';lines=path.read_text().splitlines();parts=lines[1].split(',');parts[2]='google_shop';lines[1]=','.join(parts);path.write_text('\n'.join(lines)+'\n')
  with self.assertRaisesRegex(ValueError,'inconsistent'):import_data(self.db,self.folder)
  self.assertEqual(report(self.db),before)
if __name__=='__main__':unittest.main()
