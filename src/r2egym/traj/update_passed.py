from pymongo import MongoClient

def update_submission_status(input_text):
    """
    Process test summary input and update MongoDB submission status
    """
    # Connect to MongoDB - update connection details as needed
    with MongoClient("mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@10.10.100.43:26969/") as client:
        db = client["swe_gym_plus"]
        collection = db["qwen_traces"]
        
        passed_hashes = set()
        lines = input_text.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue  # Skip empty lines
                
            # Extract hash from first token
            parts = line.split()
            if parts:
                hash_val = parts[0]
                passed_hashes.add(hash_val)
        
        print(f"Total hashes from input: {len(passed_hashes)}")
        
        # Get existing hashes from database
        existing_hashes = collection.distinct(
            "problem_statement_hash",
            {"problem_statement_hash": {"$in": list(passed_hashes)}}
        )
        existing_hashes_set = set(existing_hashes)
        
        # Find missing hashes (in input but not in DB)
        missing_hashes = passed_hashes - existing_hashes_set
        if missing_hashes:
            print("\nHashes not found in database:")
            for i, hash_val in enumerate(missing_hashes, 1):
                print(f"{i}. {hash_val}")
        else:
            print("\nAll hashes found in database!")
        
        # Update matching hashes to passed
        passed_update = collection.update_many(
            {"problem_statement_hash": {"$in": list(existing_hashes_set)}},
            {"$set": {"passed": True}}
        )
        print(f"\nUpdated {passed_update.modified_count} documents to 'passed: true'")
        
        # Update all other entries to failed
        failed_update = collection.update_many(
            {"problem_statement_hash": {"$nin": list(passed_hashes)}},
            {"$set": {"passed": False}}
        )
        print(f"Updated {failed_update.modified_count} documents to 'passed: false'")

        
with open("passed_lines.txt") as f:
    contents = f.read()
update_submission_status(contents)