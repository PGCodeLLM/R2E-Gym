import json
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import hashlib

# MongoDB configuration
MONGO_URI = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@lux-2-cyber-04:26969/"    
DB_NAME = "swe_gym_plus"
TRAIN_COLLECTION_NAME = "train"
R2E_DB_NAME = "r2e_traces"
R2E_COLLECTION_NAME = "qwen_traces.files"
# File paths
INPUT_JSONL = "TRACEGEN.jsonl"
OUTPUT_JSONL = "TRACEGEN_verified.jsonl"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
train_collection = db[TRAIN_COLLECTION_NAME]
r2e_db = client[R2E_DB_NAME]
r2e_collection = r2e_db[R2E_COLLECTION_NAME]

with open(INPUT_JSONL, "r") as infile, open(OUTPUT_JSONL, "w") as outfile:
    passed_count = 0
    verified_count = 0
    unverified_count = 0
    duplicated = 0
    cringe = 0
    for line in infile:
        try:
            entry = json.loads(line)
            problem_statement_hash = hashlib.md5(entry['problem_statement'].encode()).hexdigest()
            r2e_matches = list(r2e_collection.find({"metadata.problem_statement_hash": problem_statement_hash}))
            has_passed_entry = any(
                doc.get('metadata', {}).get('passed') is True 
                for doc in r2e_matches
            )
            if has_passed_entry:
                passed_count += 1
                base_commit = entry["ds"]["commit_hash"]
                # Find matching document in MongoDB
                matches = list(train_collection.find({"base_commit": base_commit}))
                
                if len(matches) > 1:
                    # raise DuplicateKeyError()
                    print(f"Multiple records found for commit: {base_commit}")
                    duplicated += 1
                    continue
                elif len(matches) == 1:
                    if matches[0]["verified"]:
                        train_match = matches[0]
                        # outfile.write(line)  # Write original line to output
                        new_line = {
                            "prompt": entry["prompt"],
                            "instance": {
                                "FAIL_TO_PASS": train_match["FAIL_TO_PASS"],
                                "PASS_TO_PASS": train_match["PASS_TO_PASS"],
                                "base_commit": train_match["base_commit"],
                                "instance_id": train_match["instance_id"],
                                "patch": train_match["patch"],
                                "test_patch": train_match["test_patch"],
                                "repo": train_match["repo"],
                            }
                        }
                        outfile.write(new_line)
                        verified_count += 1
                    else:
                        unverified_count += 1
                else:
                    # print(f"cring {base_commit}")
                    cringe += 1
            
        except KeyError as e:
            print(f"Key error in entry: {e}")
        except json.JSONDecodeError:
            print(f"Invalid JSON format: {line.strip()}")

    
print(f"Total verified entries: {verified_count}")
print(f"Total unverified entries: {unverified_count}")
print(f"Total duplicated entries: {duplicated}")
print(f"Total passed entries: {passed_count}")
print(f"Total cringe entries: {cringe}")