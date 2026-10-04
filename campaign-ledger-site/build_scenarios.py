from pathlib import Path
import sys,json,threading
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'campaign-ledger'))
from build_report import connect
from workflow import run
from mock_sources import server

def build():
 db=connect(':memory:');result={}
 for name,at in [('success','2026-10-03T09:00:00+00:00'),('failure','2026-10-03T09:10:00+00:00'),('correction','2026-10-03T09:15:00+00:00')]:
  service=server(name);t=threading.Thread(target=service.serve_forever,daemon=True);t.start()
  try:result[name]=run(db,f'http://127.0.0.1:{service.server_port}',at)
  finally:service.shutdown();service.server_close();t.join()
 db.close();return result
if __name__=='__main__':
 target=ROOT/'scenarios.json';target.write_text(json.dumps(build(),indent=2));print('Generated three scenarios through HTTP adapters and SQLite.')
