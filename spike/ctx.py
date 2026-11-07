#!/usr/bin/env python3
import pickle, re
found=pickle.load(open('../spike/testort_blocks.pkl','rb'))
for off,siz,b in found:
    idx=[m.start() for m in re.finditer(rb'Testort', b)]
    print(f"@0x{off:x} entpackt {siz} B, {len(idx)} x 'Testort' bei {idx[:6]}")
    for i in idx[:3]:
        pre=b[max(0,i-40):i]; post=b[i:i+60]
        print(f"    vor : {pre.hex(' ')}")
        print(f"          {pre.decode('latin-1')!r}")
        print(f"    ab  : {post.decode('latin-1')!r}")
    # reine ASCII-Strassennamen im Block
    names=set()
    for part in b.split(b'\x00'):
        if 5<=len(part)<=44:
            try: t=part.decode('utf-8')
            except UnicodeDecodeError: continue
            if re.fullmatch(r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .\-']{4,43}", t): names.add(t)
    if names: print(f"    Anzeigenamen: {sorted(names)[:12]}")
    print()
