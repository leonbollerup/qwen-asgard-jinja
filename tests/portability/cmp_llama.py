import json, sys
for t in ["qwen-asgard-v1", "sharp-naze-v1.4", "swift-original"]:
    L = json.load(open(f"llama-{t}.json")); R = json.load(open(f"ref-{t}.json"))
    same = diff = err = 0; fmts = set(); notes = []
    for k, v in L.items():
        if k.startswith("parse_"):
            continue
        if "error" in v:
            err += 1; notes.append(f"  ERROR {k}: {v['error'][:150]}"); continue
        fmts.add(v["format"])
        if v["prompt"] == R.get(k):
            same += 1
        else:
            diff += 1
            a, b = v["prompt"], R.get(k, "")
            i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            notes.append(f"  DIFF {k} @{i}: llama={a[i:i+90]!r}\n{' '*(len(k)+9)}  ref={b[i:i+90]!r}")
    print(f"=== {t}: {same} identical, {diff} different, {err} errors; formats {fmts}")
    print(*notes, sep="\n")
    for k, v in L.items():
        if k.startswith("parse_"):
            print(f"  {k}: {json.dumps(v)[:230]}")
