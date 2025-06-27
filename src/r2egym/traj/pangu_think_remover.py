import json
import re

def remove_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

infile = open("pangu_format.jsonl", "r")
outfile = open("pangu_format_thinkremoved.jsonl", "w")
for line in infile:
    entry = json.loads(line)
    for i in range(1,len(entry["data"])-1,2):
        assert entry["data"][i]["role"] == "assistant"
        entry["data"][i]["content"] = remove_think_tags(entry["data"][i]["content"])
    outfile.write(json.dumps(entry)+"\n")