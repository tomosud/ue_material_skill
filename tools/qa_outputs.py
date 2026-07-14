# -*- coding: utf-8 -*-
"""カタログQA: cppコンストラクタで Outputs を操作しているのに
カタログが「既定出力1本」のままのクラスを検出する。

usage: python tools/qa_outputs.py
対象: catalog/generated/C*.json 全部
"""
import json, glob, os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UE_PRIV = r"C:\work\unreal\UnrealEngine-release\Engine\Source"

pat = re.compile(r"UMaterialExpression(\w+)::UMaterialExpression\1\s*\(")
touch = {}
for root, _, files in os.walk(UE_PRIV):
    if "Intermediate" in root:
        continue
    for fn in files:
        if not fn.endswith(".cpp"):
            continue
        p = os.path.join(root, fn)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "UMaterialExpression" not in txt:
            continue
        for m in pat.finditer(txt):
            body = txt[m.end(): m.end() + 4000]
            nxt = re.search(r"\n\w[\w:<>*&\s]+::\w+\s*\(", body)
            if nxt:
                body = body[:nxt.start()]
            if re.search(r"\bOutputs\s*[.\[]", body):
                lines = [l.strip() for l in body.splitlines() if re.search(r"\bOutputs\s*[.\[]", l)]
                touch[m.group(1)] = (fn, lines)

flags = 0
for f in sorted(glob.glob(os.path.join(PROJ, "catalog", "generated", "C*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for k, v in d.items():
        if not isinstance(v, dict) or v.get("abstract"):
            continue
        outs = v.get("outputs", [])
        single_default = (len(outs) == 1 and outs[0].get("name", "") in ("", "Output") and not outs[0].get("mask"))
        if k in touch and single_default:
            flags += 1
            print("FLAG %s [%s] ctor in %s:" % (k, os.path.basename(f), touch[k][0]))
            for l in touch[k][1]:
                print("   ", l)
print("\nctor-Outputs classes: %d / flags: %d" % (len(touch), flags))
