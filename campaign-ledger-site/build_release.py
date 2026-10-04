from pathlib import Path
import html,json,sys,zipfile
ROOT=Path(__file__).resolve().parent
LAB=ROOT.parent/'campaign-ledger'
sys.path.insert(0,str(LAB))
from claude_brief import PROMPT
DIST=ROOT/'dist';DIST.mkdir(exist_ok=True)
scenarios=json.loads((ROOT/'scenarios.json').read_text())
assert scenarios['success']['status']=='success'
assert scenarios['failure']['status']=='failed'
assert scenarios['failure']['report']==scenarios['success']['report']
assert scenarios['correction']['status']=='success'
encoded=json.dumps(scenarios).replace('<','\\u003c')
page=(ROOT/'dashboard.html').read_text().replace('__REPORT_JSON__',encoded).replace('__CLAUDE_PROMPT__',html.escape(PROMPT))
(DIST/'index.html').write_text(page)
(DIST/'scenarios.json').write_text(json.dumps(scenarios,indent=2))
(DIST/'metrics.json').write_text(json.dumps(scenarios['success']['report'],indent=2))
(DIST/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#20232d"/><path d="M9 9h5v3h-2v8h2v3H9zm9 0h3v11h4v3h-7z" fill="white"/></svg>')
with zipfile.ZipFile(DIST/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['generate_sample.py','build_report.py','workflow.py','mock_sources.py','claude_brief.py','dashboard.html','README.md','test_report.py','test_workflow.py','test_dashboard.cjs']:
  z.write(LAB/name,'campaign-ledger/'+name)
 for folder in ['sql','data','integrations']:
  for p in (LAB/folder).iterdir():
   if p.is_file():z.write(p,'campaign-ledger/'+folder+'/'+p.name)
 for name in ['build_site.py','build_release.py','build_scenarios.py','dashboard.html','scenarios.json','check_dashboard.cjs']:
  z.write(ROOT/name,'campaign-ledger-site/'+name)
print('Built updated public workflow replay and complete source download.')
