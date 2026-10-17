#!/usr/bin/env python3
"""Exhaustive check that vLLM patch A1 and QFN.asgard agree on thinking on/off.
For every enable_thinking x reasoning_effort x inline tag (x tag position) combination: run A1's logic on the request
kwargs, render the template with the resulting kwargs (as vLLM does), and compare the template's decision (generation
prompt with an empty think block = off) with the parser's view (enable_thinking, default true).
usage: test_a1_consistency.py TOKENIZER_DIR TEMPLATE A1_PATCH_FILE"""
import itertools, re, sys, textwrap
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
tpl = Path(sys.argv[2]).read_text()
patch = Path(sys.argv[3]).read_text()
body = patch.split('new = """', 1)[1].split('"""', 1)[0]
logic = body.split("        # Asgard patch A1", 1)[1].split("        return kwargs", 1)[0]
src = "def a1(kwargs, request):\n" + textwrap.indent(textwrap.dedent("        # Asgard patch A1" + logic), "    ") + "    return kwargs\n"
ns = {}
exec(src, ns)
a1 = ns["a1"]


class Req:
    def __init__(self, messages):
        self.messages = messages


fails = n = 0
for et, eff, tag, where in itertools.product([None, True, False, "false", "true", "0", 0, 1], [None, "none", "off", "low", "medium", "xhigh", "bogus"],
                                             [None, "off", "on", "low", "medium", "high"], ["user", "system", "first-turn", "wrapped-tool"]):
    if tag is None and where != "user":
        continue
    t = f"<|think_{tag}|> " if tag else ""
    if where == "user":
        msgs = [{"role": "user", "content": t + "What is 2+2?"}]
    elif where == "system":
        msgs = [{"role": "system", "content": t + "Be brief."}, {"role": "user", "content": "What is 2+2?"}]
    elif where == "wrapped-tool":  # tag inside a user message that only wraps a tool result: data, not a control
        msgs = [{"role": "user", "content": "go"}, {"role": "assistant", "content": "", "tool_calls": [
                    {"id": "a", "type": "function", "function": {"name": "f", "arguments": {}}}]},
                {"role": "user", "content": "<tool_response>\n" + t + "data\n</tool_response>"}]
    else:  # tag in an earlier user turn (sticky)
        msgs = [{"role": "user", "content": t + "hi"}, {"role": "assistant", "content": "Hello."},
                {"role": "user", "content": "What is 2+2?"}]
    kw = {k: v for k, v in (("enable_thinking", et), ("reasoning_effort", eff)) if v is not None}
    out = a1(dict(kw), Req(msgs))
    prompt = tok.apply_chat_template(msgs, chat_template=tpl, tokenize=False, add_generation_prompt=True, **out)
    template_thinks = not prompt.endswith("<think>\n\n</think>\n\n")
    assert prompt.endswith("<think>\n") or not template_thinks, prompt[-40:]
    pv = out.get("enable_thinking", True)
    parser_thinks = bool(pv)  # vLLM's qwen3 parser: chat_kwargs.get("enable_thinking", True) used as a truth value
    if not isinstance(pv, bool):
        fails += 1
        print(f"NON-BOOL enable_thinking reaches the parser: {pv!r} (et={et!r} eff={eff} tag={tag}@{where})")
    n += 1
    if template_thinks != parser_thinks:
        fails += 1
        print(f"MISMATCH enable_thinking={et} effort={eff} tag={tag}@{where}: template thinks={template_thinks}, parser expects={parser_thinks}")
print(f"{n} combinations, {fails} mismatches")
