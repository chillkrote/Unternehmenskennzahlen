import sys,re
# page.py txt pattern [maxpages] -> prints pages matching pattern, whitespace squeezed
P=open(sys.argv[1],errors='replace').read().split("\f")
pat=re.compile(sys.argv[2],re.I); mx=int(sys.argv[3]) if len(sys.argv)>3 else 2
n=0
for i,p in enumerate(P):
    if pat.search(p):
        print(f"=== Seite {i+1}")
        for l in p.splitlines():
            if l.strip(): print(re.sub(r" {3,}","   ",l.rstrip())[:220])
        n+=1
        if n>=mx: break
