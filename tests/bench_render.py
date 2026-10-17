#!/usr/bin/env python3
"""Render time of long agent sessions (what every request pays before prefill). usage: TOKENIZER_DIR TEMPLATE..."""
import sys, time
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
TOOLS = [{"type": "function", "function": {"name": "get", "description": "Get", "parameters": {
    "type": "object", "properties": {"k": {"type": "string"}}, "required": ["k"]}}}]


def session(steps, parallel):
    msgs = [{"role": "system", "content": "You are an agent."}, {"role": "user", "content": "Do the task."}]
    for i in range(steps):
        calls = [{"id": f"c{i}_{j}", "type": "function", "function": {"name": "get", "arguments": {"k": f"v{i}_{j}"}}}
                 for j in range(parallel)]
        msgs.append({"role": "assistant", "content": "", "reasoning": f"step {i}", "tool_calls": calls})
        for j in range(parallel):
            msgs.append({"role": "tool", "tool_call_id": f"c{i}_{j}", "content": f"result {i} {j}\n" * 20})
    return msgs


for path in sys.argv[2:]:
    t = Path(path).read_text()
    for steps, par in ((150, 1), (100, 3), (300, 1)):
        m = session(steps, par)
        tok.apply_chat_template(m, tools=TOOLS, chat_template=t, tokenize=False, add_generation_prompt=True)
        t0 = time.perf_counter()
        for _ in range(3):
            tok.apply_chat_template(m, tools=TOOLS, chat_template=t, tokenize=False, add_generation_prompt=True)
        print(f"{Path(path).stem:32} {len(m):4d} messages ({steps} steps x {par} calls): {(time.perf_counter() - t0) / 3 * 1000:7.1f} ms")
