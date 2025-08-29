from datasets import load_dataset
import json

# Configuration
dataset_name = "R2E-Gym/R2EGym-SFT-Trajectories"
split = "train"
output_file = "r2egym_sft_trajectories.jsonl"

# Load dataset in streaming mode
dataset = load_dataset(dataset_name, split=split, streaming=True)

# Write to JSONL file
with open(output_file, "w", encoding="utf-8") as f:
    for row in dataset:
        # Convert to JSON string and write to file
        json_line = json.dumps(row, ensure_ascii=False)
        f.write(json_line + "\n")

print(f"Dataset saved to {output_file}")