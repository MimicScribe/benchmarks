#!/usr/bin/env python3
"""Sentence-end density: words ending in . ? ! per 1,000 words, rows as decoded (raw), by corpus.
usage: punct_recount.py label=dir ..."""
import json, glob, sys
for a in sys.argv[1:]:
    n, p = a.split('=', 1)
    tot = {'ami': [0, 0], 'earnings21': [0, 0]}
    for f in glob.glob(p + '/per-file/*_after_orphan.json'):
        fid = f.split('/')[-1].split('_')[0]
        k = 'earnings21' if fid[0].isdigit() else 'ami'
        w = ' '.join(s['text'] for s in json.load(open(f))['segments']).split()
        tot[k][0] += len(w); tot[k][1] += sum(1 for x in w if x[-1:] in '.?!')
    print(n, {k: f"{1000*v[1]/v[0]:.1f} ({v[1]}/{v[0]})" for k, v in tot.items()})
