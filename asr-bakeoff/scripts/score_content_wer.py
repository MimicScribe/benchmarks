#!/usr/bin/env python3
"""score_content_wer.py — WER on the CONTENT basis for N arms on their shared scored files.

Owner decision (2026-09-26, Parakeet Ultra switch): filler words and casual-speech rewrites
("wanna" / "want to") are not errors. Columns, each applied to reference AND hypothesis alike:
  verbatim   — score_corpus_wer.py's own normalization (its current ITN basis)
  nofill     — filled pauses removed (uh, um, mm, hmm, …)
  content    — nofill + casual forms folded to their expansion
  no-numbers — content + number words and digit tokens removed: the fair basis across arms that
               write numbers as digits vs words (numbers are scored separately by
               score_number_fidelity.py).

Usage: scripts/score_content_wer.py "label=benchmark/output/<arm>" ["label=..." ...]
Reads <arm>/per-file/<id>_after_orphan.json; references come from score_corpus_wer.reference().
"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_corpus_wer as S
from pathlib import Path
FILL = {"uh","um","mm","hmm","mhm","hm","mmhmm","mmhm","uhhuh","uhhum","ah","er","eh","erm","uhm","huh","umm","uhh","mmm"}
COLL = {"wanna":["want","to"],"gonna":["going","to"],"gotta":["got","to"],"cause":["because"],"cuz":["because"],
        "kinda":["kind","of"],"sorta":["sort","of"],"alright":["all","right"],"ok":["okay"],"lemme":["let","me"],"dunno":["don't","know"]}
import re as _re
NUMW=set("""zero oh one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen
eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion trillion
first second third fourth fifth sixth seventh eighth ninth tenth twelfth twentieth thirtieth percent point dollar dollars
cent cents euro euros pound pounds half quarter quarters""".split())
def nonum(ws):
    return [w for w in ws if w not in NUMW and not _re.search(r"\d", w)]
def fold(ws, coll):
    out=[]
    for w in ws:
        if w in FILL: continue
        if coll and w in COLL: out+=COLL[w]; continue
        out.append(w)
    return out
args=sys.argv[1:]
arms=[(a.split('=',1)[0], Path(a.split('=',1)[1])) for a in args]
ids=None
for _,p in arms:
    s={x.name.split('_after_orphan')[0] for x in (p/'per-file').glob('*_after_orphan.json')}
    ids = s if ids is None else ids & s
ids=sorted(ids)
print(f"{len(ids)} shared files")
print(f"{'arm':28} {'verbatim':>9} {'nofill':>9} {'content':>9} {'content-no-numbers':>19}   no-num ami / e21")
for name,p in arms:
    tot={b:collections.Counter() for b in ('v','n','c','x')}
    for fid in ids:
        r=S.reference(fid)
        if not r: continue
        corpus,ref=r; hyp=S.hypothesis(p,fid)
        if hyp is None: continue
        for b,(rf,hy) in {'v':(ref,hyp),'n':(fold(ref,False),fold(hyp,False)),'c':(fold(ref,True),fold(hyp,True)),
                          'x':(nonum(fold(ref,True)),nonum(fold(hyp,True)))}.items():
            s=S.score(rf,hy); e=s['sub']+s['del']+s['ins']
            tot[b]['e']+=e; tot[b]['n']+=len(rf); tot[b][corpus+'e']+=e; tot[b][corpus+'n']+=len(rf)
    w=lambda b,k='': 100*tot[b][k+'e']/max(1,tot[b][k+'n'])
    print(f"{name:28} {w('v'):8.2f}% {w('n'):8.2f}% {w('c'):8.2f}% {w('x'):18.2f}%   {w('x','ami'):6.2f}% / {w('x','earnings21'):6.2f}%")
