from __future__ import annotations
import json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CatalogTests(unittest.TestCase):
    def test_validator_passes(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts'/'validate_catalog.py')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_ambiguous_record_is_not_verified(self):
        record=json.loads((ROOT/'data'/'products'/'iso-170-70.json').read_text(encoding='utf-8'))
        self.assertEqual(record['status'],'needs-verification')
        self.assertEqual(record['confirmed_facts'],[])
        self.assertTrue(record['hypotheses'])
        self.assertTrue(record['next_verification'])

if __name__=='__main__': unittest.main()
