from r2egym.commit_models.diff_classes import FileInfo, FileDiff, FileDiffHeader, ParsedCommit
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import json

mongo_uri = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@10.10.100.43:26969/"
db_name="swe_gym_plus"
collection_name="train"
new_collection_name="r2e_instances"
mongo_client = MongoClient(mongo_uri)
db = mongo_client[db_name]
collection = db[collection_name]
new_collection = db[new_collection_name]
cursor = collection.find({"verified": True}, {
    "_id": 0,
    "last_modified": 0,
    "issue_numbers": 0,
    "created_at": 0,
})
documents = list(cursor)
for doc in documents:
    try:
        print("ahhhhhhhhhhhhhhhhhh")
        file_diffs = []
        if "patch_file_contents" in doc:
            combined_contents = doc["patch_file_contents"]
            combined_contents.update(doc["test_patch_file_contents"])
        elif "test_patch_file_contents" in doc:
            combined_contents = doc["test_patch_file_contents"]
        else:
            print("wtf?")
            continue
        for patch_file_path, patch_file_content in combined_contents.items():
            header = {
                "file": {
                    "path": patch_file_path
                }
            }
            file = FileDiff(
                old_file_content="",
                new_file_content=patch_file_content,
                header=header
            ).__dict__
            file["header"] = header
            file_diffs.append(file)
        parsed_commit = ParsedCommit(
            file_diffs=file_diffs,
            old_commit_hash=f"{doc['base_commit']}^",
            new_commit_hash=doc["base_commit"],
            commit_message="",
            commit_date = datetime.now()
        ).__dict__
        expected_output_json = {}
        for p2p in doc["PASS_TO_PASS"]:
            p2p_name = p2p.split("::")[-1]
            expected_output_json[p2p_name] = "PASSED"
        for f2p in doc["FAIL_TO_PASS"]:
            f2p_name = f2p.split("::")[-1]
            expected_output_json[f2p_name] = "PASSED"
        for f2f in doc["FAIL_TO_FAIL"]:
            f2f_name = f2f.split("::")[-1]
            expected_output_json[f2f_name] = "FAILED"
        expected_output_json = json.dumps(expected_output_json)
        doc["expected_output_json"] = expected_output_json
        parsed_commit["file_diffs"] = file_diffs
        doc["parsed_commit_content"] = parsed_commit
        new_collection.update_one(
            {"instance_id": doc["instance_id"]},
            {"$set": doc},
            upsert=True
        )
    except Exception as e:
        print(e)
        continue