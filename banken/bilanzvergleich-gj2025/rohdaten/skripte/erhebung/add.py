import json,math,openpyxl,sys
sys.path.insert(0,'.'); import parse
wb=openpyxl.load_workbook('/mnt/project-files/bilanzvergleich/Bilanzvergleich_Banken_GJ2025.xlsx',data_only=True)
K={r[3]:r for r in wb['Übersicht'].iter_rows(min_row=2,values_only=True) if r[3]}
B='/tmp/claude-0/-home-user/9059df30-471a-5482-b7c9-6ef849729b0a/scratchpad/bil2/'
new=json.load(open(B+'extra.json')) if __import__('os').path.exists(B+'extra.json') else {}
def add(nm,a,p,ta,tp,url,page,note):
    bs=K[nm][6]; sc=10**round(math.log10(bs/ta))
    m=lambda d:{x:round(v*sc,3) for x,v in d.items() if v}
    A=m(a);P=m(p)
    print(nm[:32],'BS',round(ta*sc,1),bs,'EK',P.get('ek'),K[nm][7],'Fonds',P.get('fonds'),K[nm][10],'dA',round(sum(A.values())-ta*sc,2),'dP',round(sum(P.values())-tp*sc,2))
    new[nm]={'name':nm,'source_url':url,'page':page,'aktiva':A,'passiva':P,'summe_aktiva':round(ta*sc,3),'summe_passiva':round(tp*sc,3),'note':note}
for nm,i,pa,pp,url in [('Deutsche Apotheker- und Ärztebank eG (apoBank)',101,71,72,'https://www.apobank.de/dam/jcr:a2f745c7-f83d-4724-ab10-5057effcb335/apobank-jahresfinanzbericht-2025.pdf'),
                       ('Landessparkasse zu Oldenburg',106,22,23,'https://www.lzo.com/content/dam/myif/lspk-oldenburg/work/dokumente/pdf/ihre-sparkasse/berichte/Geschaeftsjahr_2025.pdf'),
                       ('Kreissparkasse Heilbronn',105,2,3,'https://www.sparkasse-heilbronn.de/content/dam/myif/ksk-heilbronn/work/dokumente/pdf/allgemein/Geschaeftsbericht_2025.pdf')]:
    a,ea,p,ep=parse.run(i,pa,pp); add(nm,a['pos'],p['pos'],a['total'],p['total'],url,f'{pa+1}-{pp+1}','')
add('Ostsächsische Sparkasse Dresden',dict(barreserve=220809,ford_ki=3380254,ford_kunden=8924852,schuldverschr=3088783,aktien=378814,beteiligungen=29990,verb_unt=15069,treuhand_a=21773,immat=169,sachanlagen=63598,sonst_vg=4358,rap_a=9373),
    dict(verb_ki=630914,verb_kunden=13777376,treuhand_p=21773,sonst_verb=12170,rap_p=1384,rueckst=144320,nachrang=38222,fonds=890200,ek=621483),16137842,16137842,
    'https://www.ostsaechsische-sparkasse-dresden.de/content/dam/myif/ospa-dresden/work/dokumente/pdf/content/ihre_sparkasse/Bilanz.pdf?n=true',1,'Bilanz in gekürzter Fassung (alle Hauptposten, ohne Unterposten)')
add('Förde Sparkasse',dict(barreserve=130765965.26,ford_ki=1134103728.11,ford_kunden=6459860416.44,schuldverschr=1180606212.60,aktien=138126631.82,beteiligungen=98915089.68,verb_unt=6545000.00,treuhand_a=9371784.50,immat=309.00,sachanlagen=80053536.26,sonst_vg=5884615.36,rap_a=371982.86),
    dict(verb_ki=744174979.84,verb_kunden=7395005746.59,verbrieft=42441369.60,treuhand_p=9371784.50,sonst_verb=10525835.75,rap_p=843890.97,rueckst=73813153.99,nachrang=25866877.74,fonds=545500000.00,ek=397061632.91),9244605271.89,9244605271.89,
    'https://www.foerde-sparkasse.de/content/dam/myif/foerde-spk/work/dokumente/pdf/allgemein/1%20Gesch%C3%A4ftsbericht%202025.pdf','35-36','Bilanz im PDF als Bild, visuell abgelesen; Summen geprüft')
add('Sparda-Bank München eG',dict(barreserve=120729,ford_ki=2884632,ford_kunden=5211678,schuldverschr=501525,aktien=425999,beteiligungen=26104,verb_unt=24346,immat=675,sachanlagen=27263,sonst_vg=17464,rap_a=7563,akt_lat=17684),
    dict(verb_ki=534981,verb_kunden=7998756,sonst_verb=7687,rap_p=32,rueckst=58322,nachrang=76427,fonds=85000,ek=504459),9265664,9265664,
    'https://atruvia.scene7.com/is/content/atruvia/Offenlegungsbericht_OHNE_Verguetungsinfo_2025_barrierefreipdf',12,'aus Offenlegungsbericht 31.12.2025, Tabelle EU CC2 (Bilanz laut Jahresabschluss, TEUR); Aktiva rundungsbedingt 2 TEUR unter Summe')
for nm,i,pa,pp,url,fix in [('UmweltBank AG',107,54,54,'https://www.hauptversammlung.de/fileadmin/public/user_upload/UmweltBank_GB25.pdf',{}),
    ('MERKUR PRIVATBANK KGaA',108,24,24,'https://www.hauptversammlung.de/fileadmin/public/user_upload/Merkur_JA25.pdf',{'barreserve':1270223.57+33033343.06}),
    ('GRENKE BANK AG',109,5,6,'https://www.lobbyregister.bundestag.de/media/60/6d/787326/JA-2025-Grenke-Bank-AG.pdf',{})]:
    a,ea,p,ep=parse.run(i,pa,pp); a['pos'].update(fix); add(nm,a['pos'],p['pos'],a['total'],p['total'],url,f'{pa+1}-{pp+1}' if pa!=pp else pa+1,'')
a,ea,q,ep=parse.run(112,23,23)
add('Bank11 für Privatkunden und Handel GmbH',a['pos'],dict(verb_ki=606774238.06,verb_kunden=4334622168.90,sonst_verb=4190718502.39,rap_p=5603207.41,rueckst=19129537.28,nachrang=1000000.00,ek=477178843.39),a['total'],9635026497.43,
    'https://www.bank11.de/datei/jahresabschluss-bank11-fuer-privatkunden-und-handel-gmbh-2025',24,'Jahresabschluss 2025 von der Bank11-Website (Testatsexemplar)')
add('Hanseatic Bank GmbH & Co KG',dict(barreserve=139146536.16,ford_ki=1421876.11,ford_kunden=4444478465.04,schuldverschr=191011761.37,verb_unt=283250.65,immat=7764577.05,sachanlagen=6694153.18,sonst_vg=84510110.65,rap_a=1712930.56),
    dict(verb_ki=436313769.59,verb_kunden=3721326007.69,sonst_verb=7342330.71,rap_p=130378065.49,rueckst=32214482.32,nachrang=65535480.82,fonds=14000000,ek=469913524.15),4877023660.77,4877023660.77,
    'https://www.hanseaticbank.de/content/download/12232/file/HB_GB_2025.pdf',15,'Geschäftsbericht 2025 von der Bank-Website; die Übersicht enthält noch die Werte zum 31.12.2024 (Bilanzsumme 4.764 Mio. €), daher Abweichung in der Prüfspalte')
C=json.load(open(B+'cc2_res.json'))
for nm in ['Donner & Reuschel AG','Isbank AG','Stadtsparkasse München','Stadtsparkasse Düsseldorf','Stadt- und Kreissparkasse Leipzig','Kreissparkasse Böblingen','Stadtsparkasse Wuppertal']:
    e=C[nm]
    if nm=='Isbank AG':
        e['passiva'].update(verb_ki=333.85,verb_kunden=1378.14,ek=482.82); e['summe_passiva']=2212.06; e['note']=e['note'].replace('; Eigenkapital als Differenz zur Bilanzsumme','')
    if nm=='Stadtsparkasse München': e['note']+='; Eigenkapital laut CC2 1.541 Mio. €, in der Übersicht 1.533 Mio. € aus der Sitzungsvorlage der Stadt'
    if nm=='Stadtsparkasse Wuppertal': e['note']+='; Bilanzsumme laut CC2 8.312 Mio. €, Übersicht nennt 8.295 Mio. € aus Pressebericht'
    new[nm]=e; print(nm[:32],'dA',round(sum(e['aktiva'].values())-e['summe_aktiva'],2),'dP',round(sum(e['passiva'].values())-e['summe_passiva'],2))
json.dump(new,open(B+'extra.json','w'),ensure_ascii=False,indent=1); print(len(new))
