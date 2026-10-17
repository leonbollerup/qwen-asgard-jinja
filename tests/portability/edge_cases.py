#!/usr/bin/env python3
"""Client edge cases through transformers (as vLLM renders). usage: edge_cases.py TOKENIZER_DIR TEMPLATE..."""
import sys
from pathlib import Path
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(sys.argv[1])
TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a file",
          "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]
U = {"role": "user", "content": "Read a.py"}
CALL = lambda args, content="": {"role": "assistant", "content": content, "tool_calls": [
    {"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": args}}]}
RES = {"role": "tool", "tool_call_id": "c1", "content": "print(1)"}

cases = {
    "tool_content_parts": [U, CALL({"path": "a.py"}), {"role": "tool", "tool_call_id": "c1",
                           "content": [{"type": "text", "text": "print(1)"}, {"type": "text", "text": "print(2)"}]}],
    "assistant_content_none": [U, CALL({"path": "a.py"}, None), RES],
    "assistant_content_parts": [U, {"role": "assistant", "content": [{"type": "text", "text": "Hi."}]}, {"role": "user", "content": "x"}],
    "empty_arguments_dict": [U, CALL({}), RES],
    "tool_message_with_name": [U, CALL({"path": "a.py"}), {**RES, "name": "read_file"}],
    "no_type_on_tool_call": [U, {"role": "assistant", "content": "", "tool_calls": [
                             {"id": "c1", "function": {"name": "read_file", "arguments": {"path": "a.py"}}}]}, RES],
    "tool_call_flat_format": [U, {"role": "assistant", "content": "", "tool_calls": [
                              {"name": "read_file", "arguments": {"path": "a.py"}}]}, RES],
    "nested_and_list_args": [U, CALL({"path": "a.py", "opts": {"lines": [1, 2]}, "flag": True, "n": None}), RES],
    "unicode_args": [U, CALL({"path": "æøå/日本.py"}), RES],
    "empty_user": [{"role": "user", "content": ""}],
    "only_system": [{"role": "system", "content": "sys"}],
    "tool_without_preceding_call": [U, RES],
}
for path in sys.argv[2:]:
    tpl = Path(path).read_text()
    print(f"=== {Path(path).stem}")
    for name, msgs in cases.items():
        try:
            s = tok.apply_chat_template(msgs, tools=TOOLS, chat_template=tpl, tokenize=False, add_generation_prompt=True)
            tail = s.split("<|im_start|>user\n", 1)[-1][:150] if name != "only_system" else s[-80:]
            print(f"  ok    {name:28} {tail!r}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name:28} {type(e).__name__}: {str(e)[:110]}")
    # assistant prefill: last message is assistant, no generation prompt (continue_final_message)
    try:
        s = tok.apply_chat_template([U, {"role": "assistant", "content": "Sure, the file"}], chat_template=tpl,
                                    tokenize=False, add_generation_prompt=False, continue_final_message=True)
        print(f"  ok    {'prefill_continue':28} {s[-90:]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR {'prefill_continue':28} {type(e).__name__}: {str(e)[:110]}")
