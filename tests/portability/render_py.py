#!/usr/bin/env python3
"""Reference renders with transformers (jinja2 sandbox, as vLLM uses). usage: render_py.py TOKENIZER_DIR TEMPLATE OUT.json"""
import json, sys
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
tpl = open(sys.argv[2]).read()
out = {}
for c in json.load(open("cases.json")):
    try:
        out[c["name"]] = tok.apply_chat_template(c["messages"], tools=c["tools"], chat_template=tpl, tokenize=False,
                                                 add_generation_prompt=True, **c["kwargs"])
    except Exception as e:  # noqa: BLE001
        out[c["name"]] = f"ERROR {type(e).__name__}: {e}"
json.dump(out, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
print(sum(not v.startswith("ERROR") for v in out.values()), "/", len(out), "rendered")
