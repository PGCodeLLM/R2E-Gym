import json

def pretty_print_jsonl(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            # Parse each line as JSON
            json_obj = json.loads(line)
            
            # Access the trajectory_steps list
            steps = json_obj.get('trajectory_steps', [])
            
            # Print each step's step_idx and action
            for step in steps:
                step_idx = step.get('step_idx', 'N/A')
                action = step.get('action', 'N/A')
                print(f"Step {step_idx}: {action}")
            
            print("...___...___"*20)  # Add empty line between objects
# Usage
pretty_print_jsonl('traj/NON_FN_r2egym-training-trajectories_qwen.jsonl')