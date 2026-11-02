import sys,json,time
sys.path.insert(0,'/tmp/g')
from wd import q
Q={'South Korea':'Q884','China':'Q148','Australia':'Q408','India':'Q668','Greece':'Q41','Israel':'Q801','Hong Kong':'Q8646','Poland':'Q36','United Arab Emirates':'Q878','Canada':'Q16','UK':'Q145','Denmark':'Q35','Hungary':'Q28','Mexico':'Q96','Singapore':'Q334','Romania':'Q218','Lithuania':'Q37','Latvia':'Q211','Netherlands':'Q55','Brazil':'Q155','Iceland':'Q189','Croatia':'Q224','Ireland':'Q27','Portugal':'Q45','Japan':'Q17','Belgium':'Q31','Austria':'Q40','Germany':'Q183','Switzerland':'Q39','Sweden':'Q34','Norway':'Q20','Finland':'Q33','France':'Q142','Italy':'Q38','Spain':'Q29'}
import os
for land,qid in Q.items():
    fn='/tmp/g/wd_'+land.replace(' ','_')+'.json'
    if os.path.exists(fn) and os.path.getsize(fn)>5: continue
    s=f'''SELECT ?l ?isin ?tick ?exl WHERE {{ ?c wdt:P946 ?isin; wdt:P17|wdt:P159|wdt:P495 wd:{qid} . ?c rdfs:label ?l FILTER(lang(?l)="en")
    OPTIONAL{{?c p:P414 ?st. ?st ps:P414 ?ex. OPTIONAL{{?st pq:P249 ?tick}} ?ex rdfs:label ?exl FILTER(lang(?exl)="en")}} }} LIMIT 20000'''
    r=q(s)
    json.dump([{k:v['value'] for k,v in b.items()} for b in r],open(f'/tmp/g/wd_{land.replace(" ","_")}.json','w'),ensure_ascii=False)
    print(land,len(r),flush=True)
    time.sleep(65)
print('done',flush=True)
