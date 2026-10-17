// tplcheck: render chat-template cases through llama.cpp's own Jinja engine + chat layer (as llama-server does),
// then parse sample model outputs with the parser llama.cpp derives for the template.
// usage: llama-tplcheck TEMPLATE.jinja cases.json out.json
#include "chat.h"
#include "common.h"
#include "json.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

static std::string read_file(const std::string & p) {
    std::ifstream f(p);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static common_chat_templates_inputs make_inputs(const common_json & c) {
    common_chat_templates_inputs in;
    in.messages         = common_chat_msgs_parse_oaicompat(c.at("messages"));
    in.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;  // llama-server default
    if (c.contains("tools") && c.at("tools").is_array()) {
        in.tools               = common_chat_tools_parse_oaicompat(c.at("tools"));
        in.parallel_tool_calls = true;
    }
    if (c.contains("kwargs")) {
        for (const auto & [k, v] : c.at("kwargs").items()) {
            in.chat_template_kwargs[k] = v.dump();  // same as server-common.cpp
        }
    }
    auto it = in.chat_template_kwargs.find("enable_thinking");
    if (it != in.chat_template_kwargs.end()) {
        in.enable_thinking = it->second == "true";
    }
    return in;
}

int main(int argc, char ** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s TEMPLATE cases.json out.json\n", argv[0]);
        return 1;
    }
    auto tmpls = common_chat_templates_init(nullptr, read_file(argv[1]), "", "<|im_end|>");
    auto cases = common_json::parse(read_file(argv[2]));
    auto out   = common_json::object();

    for (size_t i = 0; i < cases.size(); i++) {
        const auto &  c    = cases[i];
        std::string   name = c.at("name").get<std::string>();
        common_json   r    = common_json::object();
        try {
            auto                in = make_inputs(c);
            common_chat_session s(tmpls.get(), nullptr, in, {});
            r["prompt"]            = s.prompt().str();
            r["format"]            = std::string(common_chat_format_name(s.format()));
            r["generation_prompt"] = s.generation_prompt();
            r["thinking_start"]    = s.thinking_start_tag();
        } catch (const std::exception & e) {
            r["error"] = std::string(e.what());
        }
        out[name] = r;
    }

    // parse tests: model output continues after the generation prompt
    struct ptest {
        const char * name;
        int          case_idx;  // which case's request to use
        const char * output;
    };
    auto find_case = [&](const char * n) -> int {
        for (size_t i = 0; i < cases.size(); i++) {
            if (cases[i].at("name").get<std::string>() == n) {
                return (int) i;
            }
        }
        return -1;
    };
    const ptest tests[] = {
        { "parse_single_call", find_case("tools"),
         "I need the file.\n</think>\n\n<tool_call>\n<function=read_file>\n<parameter=path>\nsrc/main.py\n</parameter>\n</function>\n</tool_call>" },
        { "parse_parallel_calls", find_case("tools"),
         "Two calls.\n</think>\n\n<tool_call>\n<function=read_file>\n<parameter=path>\nsrc/main.py\n</parameter>\n</function>\n</tool_call>\n<tool_call>\n<function=run_tests>\n<parameter=pattern>\nauth\n</parameter>\n</function>\n</tool_call>" },
        { "parse_answer", find_case("tools"), "Simple.\n</think>\n\nThe answer is 4." },
        { "parse_thinking_off", find_case("enable_thinking_false"), "The answer is 4." },
        { "parse_effort_none", find_case("effort_none"), "The answer is 4." },
        { "parse_think_off_tag", find_case("think_off_tag"), "The answer is 4." },
    };
    for (const auto & t : tests) {
        common_json r = common_json::object();
        try {
            auto                in = make_inputs(cases[(size_t) t.case_idx]);
            common_chat_session s(tmpls.get(), nullptr, in, {});
            const auto &        m = s.finish(common_chat_input(std::string(t.output)));
            r["content"]          = m.content;
            r["reasoning"]        = m.reasoning_content;
            auto calls            = common_json::array();
            for (const auto & tc : m.tool_calls) {
                calls.push_back(tc.name + " " + tc.arguments);
            }
            r["tool_calls"] = calls;
        } catch (const std::exception & e) {
            r["error"] = std::string(e.what());
        }
        out[t.name] = r;
    }

    std::ofstream(argv[3]) << out.dump(1);
    return 0;
}
