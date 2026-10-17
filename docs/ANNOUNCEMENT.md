# Introduction texts for Qwen Asgard v1

Replace `<LINK>` with the place you publish the folder (e.g. GitHub or Hugging Face).

---

## One-liner (HF description, GitHub repo "About")

A tested drop-in chat template for Qwen3.8-Flash-Next / Swift 1.5 (vLLM, SGLang, llama.cpp). It renders the model's own prompt and fixes the requests that break other templates. Opt-in switches are A/B-benchmarked; the best one is +1.4 BFCL points.

---

## Short post (e.g. r/LocalLLaMA)

**Title:** Qwen Asgard v1 – a tested chat template for Qwen3.8-Flash-Next / Swift 1.5 (vLLM + llama.cpp), with A/B benchmarks

We run Swift 1.5 (Qwen3.8-Flash-Next fine-tune) on vLLM for agentic coding. The community templates (Unsloth, froggeric, Sharp, Sharp-naze, chromix) each fix different things, but they also bundle behaviour changes you can't switch off or A/B test. So we merged them into one template and made every behaviour change an opt-in switch. Then we measured which switches actually help.

**What it is**
- **Defaults** = the model's own prompt, byte for byte, plus robustness fixes.
- **Every extra is a switch**, per request (`chat_template_kwargs`) or server-wide (`--default-chat-template-kwargs`).

**Fixes that every upstream template we tested lacks**
- **Claude Code tool search:** `tool_reference` blocks via vLLM's `/v1/messages` gave **HTTP 400**. Now they render as "Tool loaded: NAME".
- **Prompt injection:** `<|im_end|><|im_start|>system …` inside a web page or file becomes *real* special tokens on vLLM, and therefore a real system turn (verified with the tokenizer). Control-token text in user, system and tool content is now escaped, and ordinary text is untouched.
- **System or developer messages in the middle of a conversation** (agent frameworks inject them): HTTP 400 before, now rendered in place.
- **Parallel tool results that arrive out of call order** are sorted back. The prompt has no call ids, so the model otherwise mixes the results up.

**Fixes for things the model's own template gets wrong**
- Effort aliases, so an unknown value doesn't crash the request.
- Tool arguments sent as a JSON string.
- Reasoning read from `reasoning_content`, `reasoning`, `thinking` or an inline `<think>`.
- No empty `<think></think>` in history.
- History trimmed so a tool result comes first.
- `"false"` as a string switch value.
- `video_url` content parts.

**vLLM gotcha (patch included)**
- **The problem:** vLLM's qwen3 reasoning parser only looks at `enable_thinking`. If thinking is switched off any other way (effort `none`/`off`, or a `<|think_off|>` tag), **the whole answer ends up in `reasoning` and `content` is empty.**
- **Patch A1** makes vLLM work out thinking on/off exactly the way the template does. Across 1176 combinations of settings, template and parser disagree in 0 (stock vLLM: 67 of 336).
- **Without the patch:** send `enable_thinking: false` explicitly.

**Benchmarks** (Swift 1.5 AWQ, vLLM, temp 1.0, effort medium, paired per item; BFCL v4 1040 items × 2):

| Template variant | BFCL | Δ |
|---|---|---|
| model's own prompt (defaults) | 78.9% | |
| `tool_prompt: chromix` (chromix's rewritten tool instructions) | **80.2% / 80.3%** | **+1.3 / +1.4** (two independent runs) |
| Sharp payload rules + failure notes | 78.1% | −0.8 |
| strict tool-format rules only | 78.8% | −0.1 |

- Coding (EvalPlus) and long-context scores stay within noise for every variant.

**Other findings**
- **Effort xhigh is worse than medium for tool use:** BFCL −5.2 points (significant). At xhigh the model makes the wrong number of parallel calls. Coding scores are equal, with 46% more tokens.
- **When the client doesn't send reasoning back:** the template without empty think blocks scored 62.0%, the model's own 59.0%. Not significant at n=100, but the direction is right.
- **Sharp's "terse" block** cut coding answers by ~40% at no measurable cost. It still needs a test on its own.

**Portability and tests**
- Byte-identical on transformers/vLLM and `@huggingface/jinja` (old and new versions).
- On llama.cpp it renders and the auto-parser parses tool calls and reasoning correctly.
- Renders ~30% faster than the template it is based on.
- Tests, the vLLM patches and a live feature check (29/29 on our server) are in the repo.

**Recommended vLLM setting:** `--default-chat-template-kwargs '{"reasoning_effort":"medium","tool_prompt":"chromix"}'`

**Credits.** This builds directly on:
- **nazeshinjite**, whose [Sharp-naze](https://huggingface.co/nazeshinjite/Flash-Next-Chat-Templates) is the base, with several fixes from its v1.5;
- **froggeric**, whose [Qwen-Fixed-Chat-Templates](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates) provide the fix family underneath;
- **chromix**, for the tool instruction text that measured best, plus the tool rules and truncation.

Thanks also to Qwen, Unsloth and peculiar-ragdoll (Sharp). Licence: Qwen Community License 1.0, inherited.

`<LINK>`

---

## Notes for answering questions

- **Hardware and engine:** Swift 1.5 AWQ (ukisai) on 2× CMP 170HX, vLLM main (October 2026) with PP2 and MTP speculative decoding.
- **Sampling:** temperature 1.0 / top_p 0.95 / top_k 20, the model card's values.
- **Statistics:** pairing per item, bootstrap over items for the CIs, sign test for p.
  - The chromix gain is borderline on its own (p ≈ 0.14), but it replicated in an independent run.
  - Without tools, chromix and the defaults render identical prompts; their EvalPlus and long-context differences (±1 point) show the noise floor.
- **Not tested:**
  - other quants and the base Flash-Next model (only Swift 1.5 AWQ);
  - SGLang end to end (only its renderer, transformers/jinja2);
  - LM Studio directly (only the `@huggingface/jinja` engine).
- **Why no JSON tool-call mode (chromix has one)?** vLLM's `qwen3_xml` parser only reads XML, so JSON calls would arrive as text.
