import json,subprocess,hashlib,os,concurrent.futures as cf
U=json.load(open('urls_all.json'))
os.makedirs('dlall/files',exist_ok=True)
def get(u):
    h=hashlib.sha1(u.encode()).hexdigest()[:16]; out=f'dlall/files/{h}'
    if os.path.exists(out+'.meta'): return json.load(open(out+'.meta'))
    r=subprocess.run(['curl','-sSL','-m','240','-o',out,'-w','%{http_code}\t%{content_type}\t%{url_effective}',u],capture_output=True,text=True)
    code,ct,eff=(r.stdout.split('\t')+['','',''])[:3]
    ft=subprocess.run(['file','-b',out],capture_output=True,text=True).stdout.strip() if os.path.exists(out) else ''
    m={'url':u,'code':code,'ct':ct,'eff':eff,'file':ft[:60],'size':os.path.getsize(out) if os.path.exists(out) else 0,'err':r.stderr[-200:],'h':h}
    json.dump(m,open(out+'.meta','w')); return m
with cf.ThreadPoolExecutor(4) as ex: res=list(ex.map(get,U))
json.dump(res,open('dlall/results.json','w'),indent=0)
print('done',len(res))
