import json
import re
import glob
import hashlib

results = {}

r2e_traj_files = glob.glob("*trajectories*.jsonl")

def format_result_summary(pytest_line: str) -> str:
    groups = re.findall(r"([0-9]+ failed)|([0-9]+ passed)", pytest_line)
    return groups

# for file_path in r2e_traj_files:
def parse_results(file_path):
    output = ""
    output += (f"##### {file_path}\n")
    # print()
    with open(file_path, 'r') as f:
        for idx, line in enumerate(f):
            try:
                json_object = json.loads(line)
                # print(json_object.keys())
                # exit(0)
                # Process the json_object here
                pytest_result = json_object["test_output"]
                result_summary = [x for x  in pytest_result.split("\n")[-5:-1] if "s ======" in x]
                if len(result_summary) > 0:
                    result_summary = result_summary[0]
                else:
                    result_summary = "wtf"

                # format_result_summary(result_summary)

                id = hashlib.md5(json_object['problem_statement'].encode()).hexdigest()

                # print(f"{id} {len(json_object['trajectory_steps'])} {result_summary}")
                output += (f"{id} {len(json_object['trajectory_steps'])} {result_summary}\n")
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line.strip()}")
    return output
    # records =
    # reuslts[file] = []
# print(r2e_traj_files)

# r2egym_traj_file = open("")