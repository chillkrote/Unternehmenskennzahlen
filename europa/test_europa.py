import importlib.util,json,math,sys,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'europa'))
from abrufen import annual_only,identity_ok
spec=importlib.util.spec_from_file_location('terminal_europa',ROOT/'app/europa.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class EuropaTests(unittest.TestCase):
    def test_primary_override_preserves_other_statement_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'europa/daten').mkdir(parents=True);(root/'europa/ergaenzungen').mkdir()
            common={'unternehmen_id':'U000001','waehrung':'EUR','quelle':'provider','quelle_url':'https://example.com/provider'}
            (root/'europa/daten/U000001.json').write_text(json.dumps({**common,'bilanz':{'2025-12-31':{'Assets':10}},'guv':{'2025-12-31':{'Revenue':5}}}))
            (root/'europa/ergaenzungen/U000001.json').write_text(json.dumps({**common,'quelle_url':'https://example.com/report','bilanz':{'2025-12-31':{'Assets':11}},'guv':{}}))
            p=module.lade_abschluesse(root,'U000001')[0]
            self.assertEqual(p['bilanz']['Assets'],11);self.assertEqual(p['guv']['Revenue'],5)
            self.assertEqual(p['quellen']['guv']['quelle_url'],'https://example.com/provider')
            self.assertEqual(p['quellen']['bilanz']['quelle_url'],'https://example.com/report')

    def test_universe(self):
        roster=json.loads((ROOT/'europa/unternehmen.json').read_text())
        self.assertEqual(len(roster),702)
        self.assertEqual(len({c['unternehmen_id'] for c in roster}),702)
        self.assertEqual(sum('STOXX Europe 600' in c['indizes'] for c in roster),600)
        self.assertTrue(all(c['land'] for c in roster))

    def test_no_future_ttm_nonfinite_or_fabricated_zero(self):
        raw={'ticker':'TEST','info':{'financialCurrency':'EUR'},'bilanz':{'2025-12-31':{'Cash':0,'Debt':None,'NaN':math.nan,'Assets':12},'2026-12-31':{'Assets':13},'TTM':{'Assets':14}},'guv':{}}
        d=annual_only(raw,{'unternehmen_id':'U000001','name':'Test'})
        self.assertEqual(d['bilanz'],{'2025-12-31':{'Cash':0,'Assets':12}})
        self.assertEqual(d['guv'],{})

    def test_identity_rejects_wrong_company(self):
        self.assertFalse(identity_ok({'name':'Jumbo','ticker_kandidat_name':''},{'longName':'Koninklijke Ahold Delhaize N.V.'}))
        self.assertFalse(identity_ok({'name':'Jumbo','land':'Greece'},{'longName':'Jumbo Interactive','country':'Australia'}))
        self.assertFalse(identity_ok({'name':'EQT','land':'Sweden'},{'longName':'EQT Corporation','country':'United States'}))
        self.assertTrue(identity_ok({'name':'ASML HLDG'},{'longName':'ASML Holding N.V.'}))

    def test_currency_and_existing_basis_preserved(self):
        class Register:
            unternehmen={'U000001':{'land':'Switzerland'}}
            def name(self,uid):return 'Test'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'europa/daten').mkdir(parents=True)
            (root/'europa/unternehmen.json').write_text(json.dumps([{'unternehmen_id':'U000001','name':'Test','indizes':[],'land':'Switzerland'}]))
            (root/'europa/daten/U000001.json').write_text(json.dumps({'unternehmen_id':'U000001','waehrung':'CHF','quelle':'Test','quelle_url':'https://example.com','bilanz':{'2025-12-31':{'Total Assets':1000000}},'guv':{}}))
            f={'id':'U000001','name':'Test','werte':{'bilanzsumme':42}}
            module.ergaenzen(root,[f],{'U000001':f},Register())
            self.assertEqual(f['werte']['bilanzsumme'],42)
            self.assertEqual(f['abschluesse'][0]['bilanz']['Total Assets'],1000000)
            self.assertEqual(f['land_code'],'CH')

if __name__=='__main__':unittest.main()
