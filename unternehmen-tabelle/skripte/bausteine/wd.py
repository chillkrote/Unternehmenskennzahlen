import urllib.request,urllib.parse,json,sys,time
def q(sparql):
    u='https://query.wikidata.org/sparql?format=json&query='+urllib.parse.quote(sparql)
    for t in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Unternehmenskennzahlen-Erhebung/1.0','Accept':'application/sparql-results+json'}),timeout=120))['results']['bindings']
        except Exception as e:
            print('err',e,file=sys.stderr);time.sleep(65)
    return []
if __name__=='__main__':
    s='''SELECT ?c ?l ?isin ?tick ?exl WHERE { ?c wdt:P946 ?isin; wdt:P159|wdt:P17 wd:Q884 . ?c rdfs:label ?l FILTER(lang(?l)="en")
    OPTIONAL{?c p:P414 ?st. ?st ps:P414 ?ex. OPTIONAL{?st pq:P249 ?tick} ?ex rdfs:label ?exl FILTER(lang(?exl)="en")} } LIMIT 20'''
    for b in q(s): print({k:v['value'] for k,v in b.items()})
