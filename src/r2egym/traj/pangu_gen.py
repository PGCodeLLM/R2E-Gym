import json

passed_jsonl = open("passed_entries_2.jsonl", "r")
pangu_jsonl = open("pangu_format.jsonl", "a")
for line in passed_jsonl:
    passed_entry = json.loads(line)
    
    messages = passed_entry["messages"]

    line_data_list = []
    for i in range(1, len(messages), 2):
        line_data_list.append(messages[i])
        assert messages[i]["role"] == "user"
        line_data_list.append(messages[i+1])
        assert messages[i+1]["role"] == "assistant"
        assert messages[0]["role"] == "system"
        pangu_entry = {
            "meta_prompt": messages[0],
            "data": line_data_list
        }
        pangu_jsonl.write(json.dumps(pangu_entry)+'\n')
