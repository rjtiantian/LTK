import pickle,math,collections
def bb(e):
    t,p=e['t'],e['p']
    if p is None: return None
    if t=='LINE': return (min(p[0][0],p[1][0]),min(p[0][1],p[1][1]),max(p[0][0],p[1][0]),max(p[0][1],p[1][1]))
    if t in('CIRCLE','ARC'): c,r=p[0],p[1]; return (c[0]-r,c[1]-r,c[0]+r,c[1]+r)
    if t=='LWPOLYLINE': xs=[q[0] for q in p[0]]; ys=[q[1] for q in p[0]]; return (min(xs),min(ys),max(xs),max(ys)) if xs else None
    if t=='TEXT': x,y=p[0]; return (x,y,x+len(p[1])*p[2]*0.8,y+p[2])
    if t=='ELLIPSE': c=p[0];r=math.hypot(*p[1]); return (c[0]-r,c[1]-r,c[0]+r,c[1]+r)
    if t in ('INSERT','MTEXT'): x,y=p[0]; return (x,y,x,y)
    if isinstance(p,tuple) and len(p)==2 and isinstance(p[0],tuple) and len(p[0])==2 and isinstance(p[0][0],float): return (p[0][0],p[0][1],p[1][0],p[1][1])
    return None
def load(p):
    D=pickle.load(open(p,'rb')); E=D['ents']
    for e in E: e['bb']=bb(e)
    return E
def part_at(E,code,idx=0):
    H=[e for e in E if e['t']=='TEXT' and e['c']==2 and code in e['p'][1]]
    h=H[idx]; x,y=h['p'][0]; w=len(h['p'][1])*30*0.75
    # green label just above header
    G=[e for e in E if e['t']=='TEXT' and e['c']==3 and abs(e['p'][0][1]-(y+90))<80 and x-500<e['p'][0][0]<x+w+500]
    G.sort(key=lambda g:abs(g['p'][0][0]+len(g['p'][1])*12-(x+w/2)))
    gy=G[0]['p'][0][1] if G else y+90
    es=[e for e in E if e['bb'] and e['t']!='TEXT' and e['bb'][1]>gy+10 and e['bb'][3]<gy+3000 and x-800<(e['bb'][0]+e['bb'][2])/2<x+w+800]
    return h,G[0] if G else None,es
def summary(es):
    if not es: return {}
    x0=min(e['bb'][0] for e in es if e['l']!='折弯线'); y0=min(e['bb'][1] for e in es if e['l']!='折弯线')
    x1=max(e['bb'][2] for e in es if e['l']!='折弯线'); y1=max(e['bb'][3] for e in es if e['l']!='折弯线')
    circ=collections.Counter(round(2*e['p'][1],2) for e in es if e['t']=='CIRCLE')
    bend=[(e['t'],e['l'],e['c'],e['lt'],round(e['lts'],3), [ (round(a[0]-x0,2),round(a[1]-y0,2)) for a in (e['p'] if e['t']=='LINE' else [q[:2] for q in e['p'][0]])]) for e in es if e['l']=='折弯线' or e['c'] in(1,5) ]
    lay=collections.Counter((e['t'],e['l'],e['c']) for e in es)
    return dict(size=(round(x1-x0,2),round(y1-y0,2)),circ=dict(circ),bend=bend,lay=dict(lay))
