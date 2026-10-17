// Render cases.json with @huggingface/jinja (transformers.js; LM Studio uses a fork of it) and diff against
// reference renders from jinja2. usage: node render_js.mjs TEMPLATE REF.json
const { Template } = await import(process.env.JINJA_PKG ?? "@huggingface/jinja");
import fs from "node:fs";

const tpl = new Template(fs.readFileSync(process.argv[2], "utf8"));
const ref = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const cases = JSON.parse(fs.readFileSync("cases.json", "utf8"));
let same = 0, diff = 0, err = 0;
for (const c of cases) {
  let s;
  try {
    s = tpl.render({
      messages: c.messages, tools: c.tools ?? undefined, add_generation_prompt: true,
      bos_token: "", eos_token: "<|im_end|>", ...c.kwargs,
    });
  } catch (e) {
    err++; console.log(`ERROR  ${c.name}: ${String(e.message).slice(0, 160)}`); continue;
  }
  if (s === ref[c.name]) { same++; continue; }
  diff++;
  let i = 0; const r = ref[c.name] ?? "";
  while (i < s.length && s[i] === r[i]) i++;
  console.log(`DIFF   ${c.name} at char ${i}:\n   js : ${JSON.stringify(s.slice(i, i + 120))}\n   py : ${JSON.stringify(r.slice(i, i + 120))}`);
}
console.log(`\n@huggingface/jinja: ${same} identical, ${diff} different, ${err} errors (of ${cases.length})`);
