# Qwen Asgard v1: a tested chat template for Qwen3.8-Flash-Next (and Swift 1.5)

*Named after Asgard, home of the Norse gods, and of the server it was forged and tested on.*

A chat template for Qwen3.8-Flash-Next and its fine-tunes, for **vLLM, SGLang and llama.cpp**. It keeps the **model's own prompt format** and uses the **tool instructions that measured best** (+1.4 BFCL points). It adds the robustness fixes from the community templates, and every other behaviour change is an **opt-in switch**.

Every claim below comes from a test in `tests/`: render tests against the reference templates, a live end-to-end feature check, and a paired quality benchmark.

## TL;DR

- **Drop-in.** With no settings you get the measured best: the model's own prompt format with the chromix tool instructions. That gave **+1.4 BFCL points** in two independent runs, with no loss on coding (EvalPlus) or long context.
  - `tool_prompt: "qwen"` gives the model's own prompt byte for byte.
- **Recommended effort: `medium`.** `xhigh` measured −5.2 BFCL points.
- **Fixes that every upstream template we tested lacks:**
  - Claude Code tool search (HTTP 400 before);
  - prompt injection through `<|im_end|><|im_start|>system` text in web pages or files;
  - system messages in the middle of a conversation;
  - parallel tool results that arrive out of order.
- **Portable:** byte-identical on transformers/vLLM and `@huggingface/jinja`; llama.cpp renders it and parses its tool calls correctly.
- **Measured, not guessed.** 6 template variants, effort xhigh vs medium, and history handling were all benchmarked. Results below.

## Why

- **Upstream templates fail on real-world client input.**
  - A `system` message after the conversation has started returns HTTP 400 in every template we tested: the model's own, Unsloth/Sharp-naze, and chromix. So does Claude Code's tool search.
  - The model's own template also fails on an unknown `reasoning_effort` value and on tool arguments sent as a JSON string.
  - Control-token text inside a web page or file becomes real special tokens on vLLM.
- **Community templates mix fixes with behaviour changes.**
  - Fixes that are always good: aliases, string arguments, reasoning extraction.
  - Behaviour changes you may not want: terseness instructions, tool-failure notes, rewritten tool instructions.
  - You can't take one without the other, or A/B them.
- **Some failures are in the template/server interplay, not in the template alone.** See [vLLM notes](#vllm-notes).

## What you get

| | Default | Notes |
|---|---|---|
| Tool-call wire format, tool definitions, generation prompt | **byte-identical to the model's own template** | verified by `tests/render_tests.py` |
| Tool instructions | chromix+froggerick v1 text, byte-identical to that template (measured +1.4 BFCL points) | `tool_prompt: "qwen"` = the model's own text, byte for byte |
| Reasoning effort | `medium`; accepts `none`, `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultracode`, `extreme`; unknown → `medium` | never raises |
| Inline effort tags | `<\|think_off\|>`, `<\|think_on\|>`, `<\|think_low\|>` … `<\|think_extreme\|>` in a user or system message; the last one in the conversation wins and stays in effect. `<\|think_on\|>` beats `enable_thinking=false` and effort `none` | tags are stripped before rendering |
| History reasoning | read from `reasoning_content`, `reasoning`, `thinking` (string or blocks), or a leading `<think>…</think>` in content | no empty `<think>` blocks |
| `preserve_thinking` | `true`: earlier turns keep their reasoning → **100% prefix-cache reuse** across turns | `false` = the model's default (reasoning dropped before the last user turn) |
| Tool arguments as a JSON string | rendered verbatim | the model's own template crashes |
| `system`/`developer` mid-conversation | rendered in place as a system turn | every upstream template raises |
| `developer` role, several leading system messages, content-part lists | supported | |
| Claude Code tool search (`tool_reference` parts, which vLLM's Anthropic endpoint passes to the template) | rendered as `Tool loaded: NAME` | every upstream template raises → HTTP 400 |
| Tool result as the very first message (client trimmed old history) | gets its `<\|im_start\|>user` opener | the model's own template leaves it out |
| Control-token text in user, system or tool content (`<\|im_end\|>`, `<\|im_start\|>`, …; in tool results also `<tool_response>`) | written as `&lt;\|…`, so it stays text | vLLM turns it into real special tokens. A web page or file containing `<\|im_end\|><\|im_start\|>system…` would open a real system turn. Verified with the model's tokenizer. Opt out with `escape_control_tokens: false` |
| Parallel tool results that arrive out of call order | rendered in call order when the `tool_call_id`s match the calls exactly | the prompt has no call ids, so the model matches by position (vllm#61206) |
| Boolean switches as strings or ints (`"false"`, `"0"`, `"off"`, `"no"`) | understood | upstream treats `"false"` as on |
| `video_url` content parts | rendered as video | raised |
| An answer quoting `</think>` while thinking is off | kept as written | was split into fake reasoning |
| `<\|think_*\|>` tags inside a user message that only wraps tool results | treated as data | a file could switch thinking off |

**Opt-in switches** (`chat_template_kwargs`, or server-wide via `--default-chat-template-kwargs`):

| kwarg | Effect | Prompt cost |
|---|---|---|
| `tool_prompt: "qwen"` | the model's own tool instructions, byte for byte. The default is `chromix` ("Use only function names and parameters defined in `<tools>`", one closed `<tool_call>` per function, …); the XML wire format is the same either way | −46 tokens (with tools) |
| `terse: true` | Sharp v22.5 terseness block after the system prompt | +151 tokens |
| `payload_rules: true` | two tool-discipline bullets: literal parameter values only; never resend a failing call | +72 (with tools) |
| `failure_notes: true` | escalating notes inside tool results after tool failures (deterministic, so prefix-cache-stable) | 0 until a failure |
| `strict_tool_rules: true` | four tool-format bullets (line-start tags, one closed `<tool_call>` per function, no nesting, no text after a call). Already part of the default chromix text, so it only matters with `tool_prompt: "qwen"` | +67 with `qwen` |
| `max_tool_response_chars: N` | keep head and tail of tool results longer than N characters, with a marker | saves context |
| `max_tool_arg_chars: N` | keep head and tail of long tool-call argument values in history, e.g. file contents written earlier. The marker says the call was sent in full, so the model does not "repair" its own write | saves context in long agent sessions |
| `preserve_thinking: false` (alias `preserve_reasoning`) | drop earlier turns' reasoning | saves context, costs prefix reuse |

With `tool_prompt: "qwen"`, `terse`, `payload_rules`, `failure_notes` and `reasoning_effort: xhigh`, ordinary conversations render byte-identically to Sharp-naze v1.4.

**Deliberately not taken from chromix:** the automatic switch to a JSON tool-call format when names or argument values contain XML-like text. vLLM's `qwen3_xml` parser only reads the XML format, so a JSON-format call would arrive as plain text instead of a tool call. It is also off the format the model was trained on.

## Engine compatibility

The same 42 render cases were run through each Jinja engine. "Identical" means byte-identical to the transformers/jinja2 render (what vLLM uses).

| Engine | Qwen Asgard v1 | Sharp-naze v1.4 | model's own template |
|---|---|---|---|
| transformers / jinja2 (vLLM, SGLang) | 42/42 render | 39/42 | 25/42 |
| `@huggingface/jinja` 0.5.1 and 0.5.10 (transformers.js and JavaScript-based apps) | 42/42 identical | 39/42 | 25/42 |
| llama.cpp (own Jinja engine and chat layer, Oct 2026) | 41/42 render, 36 identical\* | 39/42 | 30/42 |

\* All 5 differences are llama.cpp's input normalisation, not the template: it turns string tool arguments into objects (so they render as proper XML parameters) and does not carry Anthropic-style `thinking` blocks. The 42nd case (`tool_reference` parts) is rejected by llama.cpp's own message parser before any template runs. llama.cpp builds that mark message text as input can turn off `escape_control_tokens`.

**llama.cpp output parsing.** llama.cpp derives its output parser from the template, so this was checked with model-style outputs. 6/6 parsed correctly:
- reasoning plus a single tool call;
- two parallel tool calls;
- reasoning plus an answer;
- thinking off;
- effort `none`;
- the `<|think_off|>` tag.

On llama.cpp the inline tag works without any patch, because the parser sees the generation prompt. With the model's own template, `<|think_off|>` puts the answer into `reasoning`.

**Client edge cases** (transformers render; all OK):
- tool results as content-part lists;
- `content: null` with tool calls;
- empty, nested, list, null and unicode arguments;
- tool calls without `type`, or in flat `{name, arguments}` form;
- tool messages with `name`;
- tool results without a preceding call;
- a system-only conversation (the model's template and chromix raise "No user query found");
- assistant prefill with `continue_final_message`.

**Empty `<think>` blocks.** If a client does not send reasoning back, the model's own template renders `<think>\n\n</think>` for earlier agent steps. That is the same pattern as *thinking disabled*, and it can teach the model to stop reasoning after the first tool call. Qwen Asgard (like Sharp-naze/froggeric) leaves it out. With the reasoning sent back, the step is rendered exactly as it was generated.

## Benchmark results

_Swift 1.5 AWQ on 2× CMP 170HX, vLLM, temperature 1.0 / top_p 0.95 / top_k 20, reasoning medium. Paired comparison on identical items._

**Template A/B** (2026-10-16/17). BFCL v4 has 1040 items × 2 repeats (2080 calls per variant). The diff is paired per item, the CI is an item bootstrap, and p comes from a sign test on the items that differ.

| Variant | BFCL | Δ vs the model's own text | EvalPlus (542) | Long context (180) |
|---|---|---|---|---|
| `tool_prompt: qwen` = the model's own prompt + fixes | 78.9% | | 85.8% | 98.3% |
| `tool_prompt: chromix`, **the default** (measured as the chromix v1 template, which renders identical prompts) | **80.2%** | **+1.3 pt** (−0.1 … +2.7, p 0.14) | 84.9%\* | 97.2%\* |
| `payload_rules` + `failure_notes` | 78.1% | −0.8 pt (−2.3 … +0.7, p 0.13) | | |
| `payload_rules` + `failure_notes` + `terse` | 78.3% | −0.6 pt (−2.2 … +1.1) | 85.4%, with **38% fewer output tokens** | 96.1% |
| `strict_tool_rules` | 78.8% | −0.1 pt (−1.5 … +1.3) | | |
| `payload_rules` + `failure_notes` + `strict_tool_rules` | 77.8% | −1.1 pt (−2.5 … +0.5, p 0.09) | | |

The rows below add switches on top of `tool_prompt: qwen`.

\* Without tools, chromix v1 and `tool_prompt: qwen` render **byte-identical** prompts. These two numbers therefore show the run-to-run noise (about ±1 point), not a template effect.

**Reading:**
- Only the chromix tool text helps, and mostly on irrelevance: 85.0% vs 80.5%, and live 80.3% vs 77.3%. It probably comes from "Use only function names and parameters defined in `<tools>`" and the clearer "If no function call is needed…".
- Its four format rules alone (`strict_tool_rules`) do nothing.
- Sharp's payload rules and failure notes tend to hurt.
- `terse` makes coding answers much shorter at no measurable cost on EvalPlus, but it was only tested together with the other two.

**Final version, measured again in an independent run** (Qwen Asgard v1 with its default `tool_prompt: chromix`, on vLLM with patches A1/A2):
- BFCL 80.3%: **+1.4 points** vs the model's own text (CI +0.0 … +2.9). This replicates the chromix effect.
- EvalPlus 86.5% and long context 97.2%, both inside the noise.
- Live feature check: 29/29.

**Other experiments:**

| Question | Result |
|---|---|
| Effort `xhigh` instead of `medium` | BFCL **−5.2 points** (CI −7.8 … −2.8). At xhigh the model makes the wrong number of parallel calls (parallel 86 → 70%, parallel_multiple 79 → 56%). EvalPlus is unchanged at +46% output tokens. Use `medium` for tool use. |
| `preserve_thinking: false` | multi-turn −3.5 points (not significant), and it costs prefix reuse. Keep the default. |
| Client drops reasoning: empty `<think>` blocks (the model's own template) vs none (ours) | multi-turn 59.0% vs **62.0%** (+3.0, not significant at n=100). With reasoning sent back, both score 61.5%. |

## Usage

**vLLM:**

```bash
vllm serve <model> --chat-template qwen-asgard-v1.jinja \
  --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_xml \
  --default-chat-template-kwargs '{"reasoning_effort":"medium"}'
```

The default tool text (`chromix`) is the measured best: +1.4 BFCL points in two independent runs, and equal on EvalPlus and long context. Add `"tool_prompt":"qwen"` to get the model's own prompt byte for byte.

**llama.cpp:**

```bash
llama-server -m <model.gguf> --jinja --chat-template-file qwen-asgard-v1.jinja \
  --chat-template-kwargs '{"reasoning_effort":"medium"}'
```

On llama.cpp the inline thinking tags work without any patch. Recent llama.cpp builds that mark message text as user input can set `"escape_control_tokens": false`.

**SGLang / transformers:** pass the file as the chat template. The switches are ordinary template variables.

## vLLM notes

One real problem and one minor gap sit in vLLM, not in any template. Patches are in `vllm-patches/`; apply them with `python3 A1-….py <vllm source root>`. They were written and tested against a vLLM main build from October 2026, where they patch `_effective_chat_template_kwargs` in `entrypoints/openai/chat_completion/serving.py` and `_parse_chat_message_content` in `entrypoints/chat_utils.py`. Each script refuses to apply if its anchor is not found.

1. **Thinking off.**
   - **Problem:** vLLM's qwen3 reasoning parser only knows thinking is off when `chat_template_kwargs.enable_thinking=false`, or when a top-level `reasoning_effort` is `"none"`. A template can also turn thinking off through `reasoning_effort: "off"` in kwargs or a `<|think_off|>` tag. Then the parser still expects reasoning, and **the whole answer lands in `reasoning` with empty `content`**.
   - The reverse also happens: `<|think_on|>` together with `enable_thinking=false` makes the template think while the parser expects no reasoning.
   - **Patch A1:** resolves `enable_thinking` exactly the way the template does, for both the template and the parser.
   - `tests/test_a1_consistency.py` checks every combination of `enable_thinking` (including `"false"`, `0`, `1`) × `reasoning_effort` × tag × tag position (user, system, earlier turn, inside a wrapped tool result): **1176** combinations.
   - With A1: **0** where template and parser disagree, and the parser always gets a real bool.
   - Stock vLLM disagrees in 67 of the 336 bool-only combinations. A string `"false"` also reaches its parser as "true".
   - **Without the patch:** send `enable_thinking: false` together with effort `none`, and don't use the inline tags.
2. **History reasoning** (minor).
   - **Already handled:** `/v1/chat/completions` accepts `reasoning` and renames `reasoning_content` to it, and `/v1/messages` maps Anthropic thinking blocks.
   - **Not handled:** the `/tokenize` endpoint only reads `reasoning`, and a plain-string `thinking` field is dropped everywhere.
   - **Patch A2:** adds both fallbacks. It is mainly useful for checking rendered prompts through `/tokenize`.

## Repository layout

| Path | Contents |
|---|---|
| `qwen-asgard-v1.jinja` | the template |
| `vllm-patches/` | A1 and A2 for vLLM |
| `tests/` | render tests, live feature check, render benchmark |
| `tests/reference/` | the official template, Sharp-naze v1.4 and chromix v1, used for byte-for-byte comparisons |
| `tests/portability/` | cross-engine tests (transformers, `@huggingface/jinja`, llama.cpp) |
| `docs/ANNOUNCEMENT.md` | introduction texts |
| `LICENSE`, `NOTICE.md` | licence and third-party credits |

## Tests

The CPU tests need Python with `transformers`, plus a local copy of the model's tokenizer files (`TOKENIZER_DIR`):

```bash
python tests/render_tests.py TOKENIZER_DIR
```

```bash
python tests/test_additions.py TOKENIZER_DIR
```

```bash
python tests/test_survey_fixes.py TOKENIZER_DIR
```

```bash
python tests/test_tool_prompt.py TOKENIZER_DIR
```

```bash
python tests/test_a1_consistency.py TOKENIZER_DIR qwen-asgard-v1.jinja vllm-patches/A1-thinking-off-consistency.py
```

- **`tests/render_tests.py`** compares against the reference templates in `tests/reference/`.
  - Defaults are byte-identical to the model's template.
  - With the Sharp switches on, it is byte-identical to Sharp-naze v1.4.
  - All 48 switch combinations render, with 100% prefix reuse across turns.
  - Truncation, effort aliases and odd inputs.
- **`tests/test_additions.py` and `tests/test_survey_fixes.py`** (CPU only) cover the newer behaviour:
  - `tool_reference`, the leading tool message, the alias and argument truncation;
  - escaping, checked on the token level with the model's tokenizer;
  - parallel-result order, string switches, `video_url` and wrapped tool results.
- **`tests/test_a1_consistency.py`** runs the exhaustive template/parser agreement check for patch A1.
- **`tests/test_tool_prompt.py`** proves that the default (`chromix`) reproduces the chromix v1 template (in `tests/reference/`) byte for byte, and that `tool_prompt: qwen` reproduces the model's own text.
- **`tests/bench_render.py`** times the template render for long agent sessions.
- **`tests/feature_check_live.py [BASE_URL]`** checks every feature end to end through a running vLLM server: OpenAI and Anthropic APIs, tools, parallel calls, round trips, reasoning fields, roles, and prefix reuse. Uses the env vars `API_KEY` and `MODEL`.
- **`tests/portability/`** holds the cross-engine tests.
  - `cases.py` writes the 42 cases.
  - `render_py.py` renders them with transformers.
  - `render_js.mjs` renders them with `@huggingface/jinja` and diffs.
  - `tplcheck.cpp` is a small llama.cpp tool (drop it in `examples/tplcheck/`, CMake file included). It renders through llama.cpp's chat layer and parses sample model outputs with the parser llama.cpp derives. `cmp_llama.py` compares the results.
  - `edge_cases.py` holds the client edge cases.

## Render speed

The template is rendered on the CPU for every request. Times are for transformers/jinja2, the median of 3 runs:

| Session | model's own | Sharp-naze v1.4 base | Qwen Asgard v1 |
|---|---|---|---|
| 302 messages (150 tool steps) | 7.8 ms | 29.5 ms | **21.0 ms** |
| 402 messages (100 steps × 3 parallel calls) | 11.6 ms | 47.7 ms | **40.9 ms** |
| 602 messages (300 tool steps) | 15.4 ms | 58.3 ms | **41.8 ms** |

The inherited tool-failure detection now only runs when `failure_notes` is on. Parallel-result ordering is only evaluated after a turn with more than one call. Escaping only runs on text that contains a control-token prefix.

## Credits and licence

This template stands on the work of:

- **nazeshinjite**: [Sharp-naze / Flash-Next chat templates](https://huggingface.co/nazeshinjite/Flash-Next-Chat-Templates).
  - The direct base is v1.4: the Unsloth-fixed Flash-Next template with the F1–F7 fixes, calibrated tool-failure detection and think-off prefix parity.
  - Several fixes come from v1.5: control-token escaping, the think-mode-only `</think>` split, string switches, `video_url` and the leading tool turn.
- **froggeric**: [Qwen-Fixed-Chat-Templates](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates), Apache-2.0. This is the fix family the base builds on:
  - the empty-think cure and reasoning-effort aliases;
  - string tool arguments and tool-failure escalation;
  - reasoning/thinking field extraction and sticky inline effort tags.
- **chromix**: [chromix + froggerick templates](https://github.com/leonbollerup/ai/tree/main/qwen-3.8-27b/jinja/froggeric%2Bchromix), which contributed:
  - the tool instruction text (`tool_prompt: chromix`, the measured best at +1.4 BFCL points);
  - the tool-format rules (`strict_tool_rules`);
  - `max_tool_arg_chars` / `max_tool_response_chars` and the `preserve_reasoning` alias.
- **Also:**
  - **Qwen**, for the Qwen3.8-Flash-Next chat template, under the **Qwen Community License 1.0**, which this derivative inherits (`LICENSE`; third-party licences in `NOTICE.md`).
  - **Unsloth**, for the fixed embedded template.
  - **peculiar-ragdoll**, for the [Sharp terseness block](https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates) (Apache-2.0).
  - [vllm-project/vllm#61206](https://github.com/vllm-project/vllm/issues/61206), for the parallel tool-result ordering problem.

Qwen Asgard is the merge, the switches, the A/B benchmarks, the audit and the fixes: Leon Bollerup, 2026-10-17.
