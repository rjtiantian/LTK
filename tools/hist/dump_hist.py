import ezdxf, sys, pickle
doc=ezdxf.readfile(sys.argv[1]); msp=doc.modelspace()
out=[]
for e in msp:
    t=e.dxftype(); d=dict(t=t,l=e.dxf.layer,c=e.dxf.get('color',256),lt=e.dxf.get('linetype','BYLAYER'),lts=e.dxf.get('ltscale',1.0))
    try:
        if t=='LINE': d['p']=(tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2])
        elif t=='CIRCLE': d['p']=(tuple(e.dxf.center)[:2],e.dxf.radius)
        elif t=='ARC': d['p']=(tuple(e.dxf.center)[:2],e.dxf.radius,e.dxf.start_angle,e.dxf.end_angle)
        elif t=='LWPOLYLINE': d['p']=([tuple(x) for x in e.get_points('xyb')],e.closed); d['cw']=e.dxf.get('const_width',0)
        elif t in('TEXT',):
            d['p']=(tuple(e.dxf.insert)[:2],e.dxf.text,e.dxf.height,e.dxf.get('style',''),e.dxf.get('rotation',0),tuple(e.dxf.get('align_point',(0,0,0)))[:2],e.dxf.get('halign',0),e.dxf.get('valign',0))
        elif t=='MTEXT': d['p']=(tuple(e.dxf.insert)[:2],e.text,e.dxf.char_height)
        elif t=='INSERT': d['p']=(tuple(e.dxf.insert)[:2],e.dxf.name)
        elif t=='ELLIPSE': d['p']=(tuple(e.dxf.center)[:2],tuple(e.dxf.major_axis)[:2],e.dxf.ratio,e.dxf.start_param,e.dxf.end_param)
        else:
            try:
                b=ezdxf.bbox.extents([e]); d['p']=((b.extmin.x,b.extmin.y),(b.extmax.x,b.extmax.y))
            except Exception: d['p']=None
    except Exception as ex: d['p']=None
    out.append(d)
lt={l.dxf.name:(l.dxf.get('color'),l.dxf.get('linetype')) for l in doc.layers}
pickle.dump(dict(ents=out,layers=lt,ltscale=doc.header.get('$LTSCALE')),open(sys.argv[2],'wb'))
print(len(out),lt,doc.header.get('$LTSCALE'))
