from pymongo import MongoClient
from tqdm import tqdm  # For progress bar, install with: pip install tqdm

# MongoDB connection configuration
MONGO_URI = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@lux-2-cyber-04:26969/"    
DB_NAME = "r2e_traces"
COLLECTION1_NAME = "qwen_traces.files"
COLLECTION2_NAME = "sft_qwen"

def transfer_metadata_fields():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll1 = db[COLLECTION1_NAME]
    coll2 = db[COLLECTION2_NAME]

    # Create index for faster lookups
    coll2.create_index("problem_statement_hash", background=True)

    # Get total count for progress bar
    total_docs = coll1.count_documents({})
    processed = 0
    updated = 0
    errors = 0

    print(f"Processing {total_docs} documents from {COLLECTION1_NAME}...")

    # Iterate through all documents in collection1
    for doc1 in tqdm(coll1.find(), total=total_docs):
        try:
            # Get problem statement hash from metadata
            metadata = doc1.get("metadata", {})
            problem_statement_hash = metadata.get("problem_statement_hash")
            
            if not problem_statement_hash:
                continue
            
            # Get fields to copy
            passed = metadata.get("passed")
            passed_with_errors = metadata.get("passed_with_errors_or_skipped_hashes")
            
            # Find matching documents in collection2
            matches = coll2.find({"problem_statement_hash": problem_statement_hash})
            
            # Update each matching document
            for doc2 in matches:
                update_data = {}
                
                if passed is not None:
                    update_data["passed"] = passed
                
                if passed_with_errors is not None:
                    update_data["passed_with_errors_or_skipped_hashes"] = passed_with_errors
                
                if update_data:
                    coll2.update_one(
                        {"_id": doc2["_id"]},
                        {"$set": update_data}
                    )
                    updated += 1
                    
            processed += 1

        except Exception as e:
            errors += 1
            print(f"\nError processing document: {doc1.get('_id')}")
            print(f"Error message: {str(e)}")

    # Print summary
    print("\nOperation complete!")
    print(f"• Processed documents: {processed}")
    print(f"• Updated documents: {updated}")
    print(f"• Errors encountered: {errors}")

    # Close connection
    client.close()

if __name__ == "__main__":
    transfer_metadata_fields()