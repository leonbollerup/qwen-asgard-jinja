# Patch for vllm/entrypoints/openai/chat_completion/serving.py: keep the chat template and the reasoning parser in
# agreement about thinking. The qwen3 parser only reads chat_template_kwargs.enable_thinking; Qwen Asgard (and
# Sharp-naze/froggeric-class templates) also switch thinking with reasoning_effort none/off and inline tags.
# usage: python3 A1-thinking-off-consistency.py <vllm source root>
import sys
p = sys.argv[1] + "/vllm/entrypoints/openai/chat_completion/serving.py"
s = open(p).read()
old = """    def _effective_chat_template_kwargs(
        self, request: ChatCompletionRequest
    ) -> dict[str, Any]:
        return (
            request.build_chat_params(
                self.chat_template,
                self.chat_template_content_format,
            )
            .with_defaults(self.default_chat_template_kwargs)
            .chat_template_kwargs
        )
"""
new = """    def _effective_chat_template_kwargs(
        self, request: ChatCompletionRequest
    ) -> dict[str, Any]:
        kwargs = (
            request.build_chat_params(
                self.chat_template,
                self.chat_template_content_format,
            )
            .with_defaults(self.default_chat_template_kwargs)
            .chat_template_kwargs
        )
        # Asgard patch A1: keep the chat template and the reasoning parser in agreement about thinking.
        # The parser only reads enable_thinking. Resolve it the way Qwen Asgard does: the last inline tag in
        # conversation order wins (<|think_off|> = off, <|think_on|> = on, an effort tag keeps enable_thinking);
        # without a tag, reasoning_effort none/off means off. Tags inside user messages that only wrap tool
        # results are data. String values ("false", "0", "off", "no") are normalised to a real bool.
        tags = ("<|think_off|>", "<|think_on|>", "<|think_low|>", "<|think_minimal|>", "<|think_medium|>",
                "<|think_high|>", "<|think_xhigh|>", "<|think_max|>", "<|think_ultracode|>", "<|think_extreme|>")
        last_tag = None
        for msg in request.messages or []:
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
            if role not in ("user", "system", "developer"):
                continue
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, list):
                content = "".join(str(p.get("text", "")) if isinstance(p, dict) else str(getattr(p, "text", "")) for p in content)
            if role == "user" and isinstance(content, str) and content.strip().startswith("<tool_response>") \
                    and content.strip().endswith("</tool_response>"):
                continue
            if isinstance(content, str) and "<|think_" in content:
                for tag in tags:
                    if tag in content:
                        last_tag = tag
        raw = kwargs.get("enable_thinking")
        if raw is None:
            explicit = None
        elif isinstance(raw, str):
            explicit = raw.strip().lower() not in ("", "false", "0", "off", "no", "none")
        else:
            explicit = bool(raw)
        if last_tag == "<|think_off|>":
            think = False
        elif last_tag == "<|think_on|>":
            think = True
        else:
            effort = str(kwargs.get("reasoning_effort") or "").lower()
            think = explicit is not False and (last_tag is not None or effort not in ("none", "off"))
        if think != (explicit is not False) or (raw is not None and not isinstance(raw, bool)):
            kwargs = {**kwargs, "enable_thinking": think}
        return kwargs
"""
assert s.count(old) == 1, "anchor A1 not found"
open(p, "w").write(s.replace(old, new)); print("A1 applied")
