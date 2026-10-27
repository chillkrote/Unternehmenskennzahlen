"""Erzeugt alle CSVs unter governance/ aus den Erhebungsmodulen (pilot_banken.py, boerse_*.py).
Aufruf aus dem Repo-Root: python3 governance/skripte/build.py"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(__file__))
import lib
for m in sorted(f[:-3] for f in os.listdir(os.path.dirname(__file__)) if f.startswith(('pilot_', 'boerse_')) and f.endswith('.py')):
    importlib.import_module(m)
lib.write_all()
