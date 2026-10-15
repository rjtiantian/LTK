import pickle,re,collections,bisect
exec(open('geo.py').read().split('def load')[0])
D=pickle.load(open('hist.pkl','rb'));E=D['ents']
for e in E: e['bb']=bb(e)
H=[i for i,e in enumerate(E) if e['t']=='TEXT' and e['p'] and e['c']==2 and '·' in e['p'][1] and abs(e['p'][2]-30)<1]
# rows: group headers by y (rounded)
rows=collections.defaultdict(list)
for i in H: rows[round(E[i]['p'][0][1]/50)].append(i)
# for each row, sort headers by x; column boundary = midpoints between header centers
cols=[]  # (y, x0, x1, hid)
for k,ids in rows.items():
    ids.sort(key=lambda i:E[i]['p'][0][0])
    cs=[E[i]['p'][0][0]+len(E[i]['p'][1])*30*0.7/2 for i in ids]
    for j,i in enumerate(ids):
        x0=(cs[j-1]+cs[j])/2 if j>0 else cs[j]-3000
        x1=(cs[j]+cs[j+1])/2 if j<len(ids)-1 else cs[j]+3000
        cols.append((E[i]['p'][0][1],x0,x1,i))
# index cols by x-range for lookup
cols.sort()
parts=collections.defaultdict(list)
ys=sorted(set(c[0] for c in cols))
byy=collections.defaultdict(list)
for c in cols: byy[c[0]].append(c)
for idx,e in enumerate(E):
    if not e['bb'] or idx in H: continue
    cx=(e['bb'][0]+e['bb'][2])/2; y=e['bb'][1]
    # nearest row below within 6000
    k=bisect.bisect_right(ys,y)-1
    found=None
    while k>=0 and y-ys[k]<8000:
        for c in byy[ys[k]]:
            if c[1]<=cx<c[2]: found=c[3]; break
        if found is not None: break
        k-=1
    if found is not None: parts[found].append(idx)
out=[]
for hid,ids in parts.items():
    out.append(dict(h=E[hid]['p'][1],hp=E[hid]['p'][0],ids=ids))
pickle.dump(out,open('parts.pkl','wb'))
print(len(H),len(out),sum(len(p['ids']) for p in out),len(E))
