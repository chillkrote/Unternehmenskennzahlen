#!/bin/bash
cd /home/user/unternehmenskennzahlen
python3 unternehmen-tabelle/skripte/batch_anreichern.py 10 2>&1 | cut -c1-200
C=$(python3 -c "import csv;print(max(int(r['charge']) for r in csv.DictReader(open('unternehmen-tabelle/anreicherung/stand.csv',encoding='utf-8'))))")
git add -A unternehmen-tabelle import && git commit -q -m "Anreicherung Block $C: 10 Unternehmen (Stammdaten, Kennzahlen, Berichtsabgleich)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KHLoUDiuFaDiyzb456u9hE" && git push -q origin claude/tabelle-kennzahlen 2>&1 | grep -i -E "error|rejected" ; echo "block $C gepusht"
