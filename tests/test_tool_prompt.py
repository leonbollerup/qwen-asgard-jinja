#!/usr/bin/env python3
"""tool_prompt=chromix must reproduce chromix+froggerick v1 byte for byte wherever the two templates agree on history
handling (reasoning sent back); tool_prompt default must equal the model's own text.
usage: python tests/test_tool_prompt.py TOKENIZER_DIR [TEMPLATE] [CHROMIX_TEMPLATE]"""
import sys
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "tests" / "reference"
T = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "QFN.asgard.v1.jinja").read_text()
C = Path(sys.argv[3] if len(sys.argv) > 3 else REF / "chromix-froggerick-v1.jinja").read_text()
O = (REF / "qwen3.8-flash-next-official.jinja").read_text()
TOOLS = [{"type": "function", "function": {"name": "get_weather", "description": "Current weather",
          "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
         {"type": "function", "function": {"name": "get_time", "description": "Time", "parameters": {"type": "object", "properties": {}}}}]
SYS = {"role": "system", "content": "You are an agent."}
U = {"role": "user", "content": "Weather and time in Oslo?"}
CALL = {"role": "assistant", "content": "", "reasoning": "Two calls.", "tool_calls": [
    {"id": "a", "type": "function", "function": {"name": "get_weather", "arguments": {"city": "Oslo"}}},
    {"id": "b", "type": "function", "function": {"name": "get_time", "arguments": {}}}]}
RA, RB = {"role": "tool", "tool_call_id": "a", "content": "Rain"}, {"role": "tool", "tool_call_id": "b", "content": "10:00"}
A = {"role": "assistant", "content": "Rain, 10:00.", "reasoning": "Answer."}
U2 = {"role": "user", "content": "And Lima?"}
fails = []
cases = {"first turn": [U], "with system": [SYS, U], "parallel history": [SYS, U, CALL, RA, RB],
         "multi-turn": [SYS, U, CALL, RA, RB, A, U2]}
for name, msgs in cases.items():
    for kw in ({"reasoning_effort": "medium"}, {"reasoning_effort": "xhigh"}, {"reasoning_effort": "low"}, {"enable_thinking": False}):
        c = tok.apply_chat_template(msgs, tools=TOOLS, chat_template=C, tokenize=False, add_generation_prompt=True, **kw)
        t = tok.apply_chat_template(msgs, tools=TOOLS, chat_template=T, tokenize=False, add_generation_prompt=True, tool_prompt="chromix", **kw)
        ok = c == t
        if not ok:
            i = next((i for i, (x, y) in enumerate(zip(c, t)) if x != y), min(len(c), len(t)))
            fails.append(f"{name} {kw}: chromix={c[i:i + 70]!r} ours={t[i:i + 70]!r}")
        print(("PASS " if ok else "FAIL ") + f"tool_prompt=chromix == chromix v1: {name} {kw}")
    o = tok.apply_chat_template(msgs[:2] if name != "first turn" else msgs, tools=TOOLS, chat_template=O, tokenize=False, add_generation_prompt=True, reasoning_effort="medium")
    d = tok.apply_chat_template(msgs[:2] if name != "first turn" else msgs, tools=TOOLS, chat_template=T, tokenize=False, add_generation_prompt=True, reasoning_effort="medium")
    print(("PASS " if o == d else "FAIL ") + f"default tool_prompt == model's own text ({name}, first turn)")
    if o != d:
        fails.append(f"default differs from model's own: {name}")
q = tok.apply_chat_template([U], tools=TOOLS, chat_template=T, tokenize=False, add_generation_prompt=True, tool_prompt="QWEN")
print(("PASS " if q == tok.apply_chat_template([U], tools=TOOLS, chat_template=T, tokenize=False, add_generation_prompt=True) else "FAIL ") + "tool_prompt='QWEN' = default")
print("\nALL PASS" if not fails else "\n" + "\n".join(fails))
