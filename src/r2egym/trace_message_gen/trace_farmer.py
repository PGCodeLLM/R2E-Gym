import json
import hashlib
from trace_farmers_shed import system_prompt, instance_prompt

def create_message_trace(json_line: dict):
    messages = []

    problem_statement = json_line["problem_statement"]
    problem_statement_hash = hashlib.md5(problem_statement.encode()).hexdigest()

    #Create system message
    system_message = {
        "role": "system",
        "content": system_prompt
    }
    messages.append(system_message)

    #Create first user-assistant pair
    user_content = instance_prompt.format(
        problem_statement=problem_statement
    )
    user_message = {
        "role": "user",
        "content": user_content
    }
    assistant_content = '\n'.join([json_line["trajectory_steps"][0]["thought"],json_line["trajectory_steps"][0]["action"]])
    assistant_message = {
        "role": "assistant",
        "content": assistant_content
    }
    messages.append(user_message)
    messages.append(assistant_message)

    #Create remaining user-message pairs
    for i in range(1,len(json_line["trajectory_steps"])):
        user_content = json_line["trajectory_steps"][i]["observation"]
        user_message = {
            "role": "user",
            "content": user_content
        }
        assistant_content = '\n'.join([json_line["trajectory_steps"][i]["thought"],json_line["trajectory_steps"][i]["action"]])
        assistant_message = {
            "role": "assistant",
            "content": assistant_content
        }
        messages.append(user_message)
        messages.append(assistant_message)
    message_trace = {
        "problem_statement_hash": problem_statement_hash,
        "messages": messages
    }
    return message_trace


def run_trace_farmer_for_all(input_file_name, output_file_name):
    input_f = open(input_file_name,"r")
    output_f = open(output_file_name,"a")
    for line in input_f:
        line_trace = create_message_trace(json.loads(line))
        output_f.write(json.dumps(line_trace)+'\n')

input_file_name = "NON_FN_r2egym-training-trajectories_qwen.jsonl"
output_file_name = "qwen_traces.jsonl"
run_trace_farmer_for_all(input_file_name, output_file_name)