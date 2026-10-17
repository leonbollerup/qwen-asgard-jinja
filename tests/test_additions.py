#!/usr/bin/env python3
"""Tests for the v2 additions: tool_reference, leading tool message, tag-only mid system, preserve_reasoning alias,
max_tool_arg_chars. usage: test_v2_extras.py TOKENIZER_DIR TEMPLATE (vLLM venv python)"""
import sys
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
T = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "qwen-asgard-v1.jinja").read_text()
TOOLS = [{"type": "function", "function": {"name": "write_file", "description": "Write a file",
          "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                         "required": ["path", "content"]}}}]
U = {"role": "user", "content": "Write big.txt"}
BIG = "line\n" * 2000
CALL = {"role": "assistant", "content": "", "reasoning": "Write it.", "tool_calls": [
    {"id": "c1", "type": "function", "function": {"name": "write_file", "arguments": {"path": "big.txt", "content": BIG}}}]}
RES = {"role": "tool", "tool_call_id": "c1", "content": "ok"}
A = {"role": "assistant", "content": "Done.", "reasoning": "R-MARK"}
U2 = {"role": "user", "content": "Thanks"}
fails = []


def r(msgs, **kw):
    return tok.apply_chat_template(msgs, tools=TOOLS, chat_template=T, tokenize=False, add_generation_prompt=True, **kw)


def check(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        fails.append(m)


# preserve_reasoning alias
base = r([U, A, U2])
check("R-MARK" in base, "default keeps earlier reasoning")
check("R-MARK" not in r([U, A, U2], preserve_reasoning=False), "preserve_reasoning=false drops it")
check(r([U, A, U2], preserve_reasoning=False) == r([U, A, U2], preserve_thinking=False), "alias renders identically")
check(r([U, A, U2], preserve_thinking=None) == base, "preserve_thinking=null = default")
# max_tool_arg_chars
full = r([U, CALL, RES])
cut = r([U, CALL, RES], max_tool_arg_chars=1000)
check(BIG.strip() in full and "omitted from this history view" not in full, "default: arguments untouched")
check("omitted from this history view" in cut and len(cut) < len(full) - 8000, "max_tool_arg_chars=1000 shortens the argument")
check(cut == r([U, CALL, RES], max_tool_arg_chars=1000), "truncation is deterministic")
p1 = r([U, CALL, RES], max_tool_arg_chars=1000)
p2 = r([U, CALL, RES, {"role": "assistant", "content": "Done."}, U2], max_tool_arg_chars=1000)
check(p2.startswith(p1.rsplit("<|im_start|>assistant\n", 1)[0]), "prefix stable across turns with truncation on")
# tool_reference / leading tool / tag-only system
tr = r([U, CALL, {"role": "tool", "tool_call_id": "c1", "content": [{"type": "tool_reference", "name": "write_file"}]}])
check("<tool_response>\nTool loaded: write_file\n</tool_response>" in tr, "tool_reference renders the tool name")
lt = r([RES, U])
check("<|im_start|>user\n<tool_response>\nok\n</tool_response><|im_end|>" in lt, "leading tool message gets its user opener")
ms = r([U, A, {"role": "system", "content": "<|think_off|>"}, U2])
check("<|im_start|>system\n<|im_end|>" not in ms and ms.endswith("<think>\n\n</think>\n\n"), "tag-only mid system: no empty turn, tag applied")
print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
