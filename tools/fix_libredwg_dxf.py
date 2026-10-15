# Repair LibreDWG dwg2dxf output: long strings broken across lines without group code
import re,sys
code=re.compile(rb'^\s*-?\d{1,4}$')
for f in sys.argv[1:]:
    b=open(f,'rb').read()
    b=re.sub(rb'(?<!\r)\n',b'',b)
    lines=b.split(b'\r\n')
    if lines and lines[-1]==b'': lines.pop()
    out=[];i=0;changed=False
    while i<len(lines):
        out.append(lines[i]); out.append(lines[i+1] if i+1<len(lines) else b'')
        i+=2
        while i<len(lines) and not code.match(lines[i]):
            out[-1]+=lines[i]; i+=1; changed=True
    nb=b'\r\n'.join(out)+b'\r\n'
    open(f,'wb').write(nb)
