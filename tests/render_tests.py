#!/usr/bin/env python3
"""Render tests for qwen-asgard-v1.jinja. usage: python tests/render_tests.py TOKENIZER_DIR (needs transformers)."""
import difflib, itertools, json, sys
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "tests" / "reference"
M = (ROOT / "qwen-asgard-v1.jinja").read_text()
ORIG = (REF / "qwen3.8-flash-next-official.jinja").read_text()
SHARP = (REF / "sharp-naze-v1.4.jinja").read_text() if (REF / "sharp-naze-v1.4.jinja").exists() else None  # removed from HF on 2026-10-16

TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
         {"type": "function", "function": {"name": "run_tests", "description": "Run tests", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": []}}}]
SYS = {"role": "system", "content": "You are a coding agent."}
U1 = {"role": "user", "content": "Open src/main.py and run the tests."}
CALL = {"role": "assistant", "content": "", "reasoning": "Read first.", "tool_calls": [
    {"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": {"path": "src/main.py"}}},
    {"id": "c2", "type": "function", "function": {"name": "run_tests", "arguments": {"pattern": "auth"}}}]}
R1 = {"role": "tool", "tool_call_id": "c1", "content": "def main():\n    print('hi')\n" + "x = 1\n" * 400}
R2 = {"role": "tool", "tool_call_id": "c2", "content": "FAILED tests/test_auth.py::test_login\nCommand exited with code 1"}
A2 = {"role": "assistant", "content": "One auth test fails.", "reasoning": "Summarize."}
U2 = {"role": "user", "content": "Fix it."}

fails = []
def check(cond, msg):
    if not cond:
        fails.append(msg)

def r(tpl, msgs, tools=None, **kw):
    return tok.apply_chat_template(msgs, tools=tools, chat_template=tpl, tokenize=False, add_generation_prompt=True, **kw)

# 1. defaults == model's own template text (both at medium); only difference allowed: history reasoning preserved
o = r(ORIG, [SYS, U1], tools=TOOLS, reasoning_effort="medium")
m = r(M, [SYS, U1], tools=TOOLS)
check(o == m, "defaults: tools+system prompt differs from the model's own template")
print("1. defaults vs model's own template (first turn, tools, medium):", "IDENTICAL" if o == m else "DIFFERENT")
if o != m:
    for l in difflib.unified_diff(o.splitlines(), m.splitlines(), lineterm="", n=0):
        print("   ", l[:160])

# 2. sharp-equivalent: terse+payload+failure_notes on, effort xhigh == Sharp-naze v1.4 output
for msgs in ([SYS, U1], [SYS, U1, CALL, R1, R2], [U1]) if SHARP else []:
    s = r(SHARP, msgs, tools=TOOLS)
    m = r(M, msgs, tools=TOOLS, terse=True, payload_rules=True, failure_notes=True, reasoning_effort="xhigh")
    check(s == m, f"sharp-equivalent differs for {len(msgs)} messages")
print("2. terse+payload_rules+failure_notes+xhigh == Sharp-naze v1.4:", ("IDENTICAL" if not [f for f in fails if 'sharp' in f] else "DIFFERENT") if SHARP else "SKIPPED (sharp-naze-v1.4.jinja not present)")

# 3. every toggle combination renders; prefix reuse turn1->turn2 is 100% and tool flows are deterministic
keys = ["terse", "payload_rules", "failure_notes", "strict_tool_rules"]
worst = 1.0
for combo in itertools.product([False, True], repeat=4):
    kw = dict(zip(keys, combo))
    for extra in ({}, {"max_tool_response_chars": 600}, {"preserve_thinking": False}):
        k2 = {**kw, **extra}
        p1 = r(M, [SYS, U1], tools=TOOLS, **k2)
        gen = "Summarize.\n</think>\n\nOne auth test fails.<|im_end|>\n"
        p2 = r(M, [SYS, U1, A2, U2], tools=TOOLS, **k2)
        seq = p1 + gen
        n = 0
        for a, b in zip(seq, p2):
            if a != b:
                break
            n += 1
        reuse = n / len(seq)
        if not extra.get("preserve_thinking", True) is False:
            check(reuse == 1.0, f"prefix reuse {reuse:.2%} with {k2}")
            worst = min(worst, reuse)
        h1 = r(M, [SYS, U1, CALL, R1, R2], tools=TOOLS, **k2)
        h2 = r(M, [SYS, U1, CALL, R1, R2], tools=TOOLS, **k2)
        check(h1 == h2, f"non-deterministic tool history with {k2}")
print(f"3. 16 toggle combos x 3 extras render; worst prefix reuse (preserve_thinking on): {worst:.0%}")

# 4. truncation
h = r(M, [SYS, U1, CALL, R1, R2], tools=TOOLS, max_tool_response_chars=600)
check("characters truncated" in h and "x = 1" in h, "truncation marker missing")
seg = h.split("<tool_response>\n")[1].split("\n</tool_response>")[0]
print(f"4. truncation 600: first tool result rendered as {len(seg)} chars ({'OK' if len(seg) < 700 else 'TOO LONG'}); marker: {'characters truncated' in seg}")

# 5. effort aliases + odd inputs never raise
for eff in ["none", "off", "minimal", "low", "medium", "high", "xhigh", "max", "ultracode", "extreme", "bogus", None]:
    try:
        r(M, [U1], **({} if eff is None else {"reasoning_effort": eff}))
    except Exception as e:  # noqa: BLE001
        check(False, f"effort {eff}: {e}")
try:
    r(M, [SYS, U1, {**CALL, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{\"path\": \"a\"}"}}]}, R1], tools=TOOLS)
    r(M, [U1, {"role": "assistant", "content": "x", "reasoning_content": "y"}, U2])
    r(M, [U1, {"role": "assistant", "content": "x", "thinking": [{"type": "thinking", "thinking": "y"}]}, U2])
    r(M, [U1], enable_thinking=False)
except Exception as e:  # noqa: BLE001
    check(False, f"odd input raised: {e}")
low = r(M, [U1], reasoning_effort="low"); med = r(M, [U1], reasoning_effort="medium"); unk = r(M, [U1], reasoning_effort="bogus")
check("effort is set to low" in low and med == unk, "effort mapping wrong")
print("5. effort aliases/odd inputs:", "OK" if not [f for f in fails if 'effort' in f or 'odd' in f] else "FAIL")

# 6. token cost per toggle (tools request)
base = len(tok.encode(r(M, [SYS, U1], tools=TOOLS), add_special_tokens=False))
for k in keys:
    n = len(tok.encode(r(M, [SYS, U1], tools=TOOLS, **{k: True}), add_special_tokens=False))
    print(f"6. +{k}: {n - base:+d} prompt tokens (base {base})")

print("\nFAILS:" if fails else "\nALL TESTS PASS", *fails, sep="\n  ")
