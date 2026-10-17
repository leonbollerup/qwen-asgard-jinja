# Notice

**qwen-asgard-v1.jinja** is a derivative of the Qwen3.8-Flash-Next chat template and is distributed under the **Qwen Community License 1.0** (see `LICENSE`, copyright (c) 2026 Qwen). Please read its conditions before commercial use, in particular:
- the model name must be displayed above 100M monthly active users or US$20M monthly revenue;
- a separate licence is needed for Model-as-a-Service and AI Work Assistant businesses.

## Third-party work in this template

| Work | Author | Licence | What is used |
|---|---|---|---|
| Qwen3.8-Flash-Next chat template | Qwen | Qwen Community License 1.0 | the prompt format, tool format and generation prompt |
| Unsloth-fixed Flash-Next template | Unsloth | Qwen Community License 1.0 | merged system/developer messages, tool-calling fixes |
| [Sharp-naze / Flash-Next chat templates](https://huggingface.co/nazeshinjite/Flash-Next-Chat-Templates) v1.4 and v1.5 | nazeshinjite | Qwen Community License 1.0 | the direct base (v1.4); several v1.5 fixes |
| [Qwen-Fixed-Chat-Templates](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates) | froggeric | Apache-2.0 | the F1–F7 fix family (empty-think cure, effort aliases, string tool arguments, failure escalation, reasoning fields, inline tags) |
| [Qwen-Sharp-Chat-Templates](https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates) v22.5.0 | peculiar-ragdoll | Apache-2.0 | the terseness block (`terse`) |
| [chromix + froggerick templates](https://github.com/leonbollerup/ai/tree/main/qwen-3.8-27b/jinja/froggeric%2Bchromix) | chromix | see source | the tool instruction text (`tool_prompt: chromix`), `strict_tool_rules`, truncation, `preserve_reasoning` alias |

## Other files

- `vllm-patches/` modifies vLLM (Apache-2.0, vllm-project). The patch scripts contain short excerpts of vLLM source as anchors and are provided under Apache-2.0.
- `tests/reference/` holds unmodified copies of three reference templates, used by the tests:
  - the official Qwen3.8-Flash-Next template;
  - Sharp-naze v1.4 (no longer in its repo since 2026-10-16);
  - chromix+froggerick v1.

  Each keeps its own licence.
