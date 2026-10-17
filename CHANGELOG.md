# Changelog

## v1 (2026-10-17)

First release.

- **Base:** Sharp-naze v1.4. Every behaviour change is an opt-in switch, and the defaults render the model's own prompt byte for byte.
- **Switches:**
  - `tool_prompt` (`qwen` | `chromix`), `terse`, `payload_rules`, `strict_tool_rules`, `failure_notes`;
  - `max_tool_response_chars`, `max_tool_arg_chars`;
  - `preserve_thinking` (alias `preserve_reasoning`), `escape_control_tokens`;
  - `reasoning_effort` with aliases (default medium).
- **Fixes that every tested upstream template lacks:**
  - Claude Code tool search (`tool_reference`);
  - control-token escaping (prompt injection);
  - system/developer messages mid-conversation;
  - parallel tool results that arrive out of call order.
- **Fixes vs the model's own template:**
  - effort aliases; string tool arguments;
  - reasoning from `reasoning_content`, `reasoning`, `thinking` or an inline `<think>`;
  - no empty `<think>` blocks; leading tool result; string switch values;
  - `video_url`; a think-off answer quoting `</think>`; tags inside wrapped tool results.
- **Speed:** renders about 30% faster than Sharp-naze v1.4.
- **vLLM:** patches A1 (thinking on/off agreement with the parser) and A2 (history reasoning from `thinking` and through `/tokenize`).
- **Measured** on Swift 1.5 AWQ / vLLM: `tool_prompt: chromix` gives +1.4 BFCL points (replicated); effort xhigh gives −5.2 BFCL points vs medium.
