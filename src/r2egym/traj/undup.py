import json
import hashlib
from pymongo import MongoClient
from tqdm import tqdm
from collections import defaultdict

# Configuration
MONGO_URI = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@lux-2-cyber-04:26969/"    
DB_NAME = "r2e_traces"
COLLECTION_NAME = "sft_qwen"
INPUT_JSONL = "NON_FN_r2egym-training-trajectories_qwen.jsonl"
OUTPUT_JSONL = "TRACEGEN.jsonl"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Dictionary to store the latest occurrence of each hash
latest_entries = {}

with open(INPUT_JSONL, "r") as infile:
    for line in tqdm(infile, desc="Processing entries"):
        try:
            entry = json.loads(line)
            problem = entry.get("problem_statement")
            
            if not problem:
                continue
            
            # Generate MD5 hash
            problem_hash = hashlib.md5(problem.encode()).hexdigest()
            
            # Check MongoDB for existing hash
            if collection.count_documents({"problem_statement_hash": problem_hash}, limit=1):
                # Store the latest entry for this hash
                latest_entries[problem_hash] = line
                
        except json.JSONDecodeError:
            print(f"Error decoding line: {line.strip()}")
        except KeyError:
            print(f"Missing 'problem_statement' in entry: {line.strip()}")

# Write only the latest entry for each duplicate hash
with open(OUTPUT_JSONL, "w") as outfile:
    for line in latest_entries.values():
        outfile.write(line)

print(f"\nDuplicate detection complete. Found {len(latest_entries)} unique duplicates.")
print(f"Total entries processed: {len(latest_entries)}")
print(f"Latest occurrences saved to {OUTPUT_JSONL}")