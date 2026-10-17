# Patch for vllm/entrypoints/chat_utils.py: accept assistant history reasoning from `reasoning_content` and a
# plain-string `thinking`, not only `reasoning`. /v1/chat/completions already renames reasoning_content (request
# validator) and /v1/messages maps thinking blocks; this mainly fixes /tokenize and the `thinking` string field.
# usage: python3 A2-history-reasoning-fields.py <vllm source root>
import sys
p = sys.argv[1] + "/vllm/entrypoints/chat_utils.py"
s = open(p).read()
old = """    reasoning = message.get("reasoning")

    if content is None:"""
new = """    reasoning = message.get("reasoning")
    # Asgard patch A2: fall back to the other common field names for assistant reasoning in history.
    if reasoning is None:
        reasoning = message.get("reasoning_content")  # type: ignore[assignment]
    if reasoning is None and isinstance(message.get("thinking"), str):
        reasoning = message.get("thinking")  # type: ignore[assignment]

    if content is None:"""
assert s.count(old) == 1, "anchor A2 not found"
open(p, "w").write(s.replace(old, new)); print("A2 applied")
