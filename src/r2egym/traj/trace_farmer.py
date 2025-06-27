import json
import hashlib
from trace_farmers_shed import system_prompt, instance_prompt
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from hashbrowns import get_passed
from r2egym_results_parser import parse_results
import gridfs


MONGO_URI = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@lux-2-cyber-04:26969/"    
DATABASE_NAME = "r2e_traces"
COLLECTION_NAME = "sft_qwen"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
collection = db[COLLECTION_NAME]


def upsert_dict_to_gridfs(db, data_dict):
    """
    Upserts a Python dictionary to GridFS using 'problem_statement_hash' as unique key
    """
    fs = gridfs.GridFS(db, "qwen_traces")
    # print(data_dict["trajectory_steps"][0].keys())
    # Extract the unique identifier
    problem_hash = data_dict.get('problem_statement_hash')
    passed = data_dict.get('passed')
    passed_with_errors_or_skipped_hashes = data_dict.get('passed_with_errors_or_skipped_hashes')

    max_step = 0

    if not problem_hash:
        raise ValueError("Dictionary must contain 'problem_statement_hash' field")

    combined_step_time = 0
    total_prompt_tokens = 0
    total_tokens = 0
    max_tokens = 0
    num_steps = 0
    tool_call_count = {}
    for step in data_dict["trajectory_steps"]:
        combined_step_time += step["total_step_time"]
        total_prompt_tokens += step["token_usage_prompt"]
        total_tokens += step["token_usage_total"]
        if step["token_usage_total"] > max_tokens:
            max_tokens = step["token_usage_total"]
        num_steps += 1
        if step["step_idx"] > max_step:
            max_step = step["step_idx"]
        stripped_action = step["action"].split('\n')[0][10:-1]
        if stripped_action == "":
            stripped_action = "EMPTY_CALL"
        if stripped_action in tool_call_count:
            tool_call_count[stripped_action] += 1
        else:
            tool_call_count[stripped_action] = 1
    # Convert dictionary to bytes for GridFS storage
    max_step += 1
    assert max_step == num_steps
    file_data = json.dumps(data_dict).encode('utf-8')

    # Check for existing file with same hash
    existing_file = fs.find_one({'metadata.problem_statement_hash': problem_hash})
    
    if existing_file:
        # Update existing file
        fs.delete(existing_file._id)
        new_id = fs.put(
            file_data, metadata={
                'problem_statement_hash': problem_hash,
                'passed': passed,
                'passed_with_errors_or_skipped_hashes': passed_with_errors_or_skipped_hashes,
                'combined_step_time': combined_step_time,
                'total_prompt_tokens': total_prompt_tokens,
                'total_tokens': total_tokens,
                'max_tokens': max_tokens,
                "num_steps": num_steps,
                "tool_call_count": tool_call_count
                }
            )
        return {'status': 'updated', 'id': new_id}
    else:
        # Insert new file
        new_id = fs.put(
            file_data, metadata={
                'problem_statement_hash': problem_hash,
                'passed': passed,
                'passed_with_errors_or_skipped_hashes': passed_with_errors_or_skipped_hashes,
                'combined_step_time': combined_step_time,
                'total_prompt_tokens': total_prompt_tokens,
                'total_tokens': total_tokens,
                'max_tokens': max_tokens,
                "num_steps": num_steps,
                "tool_call_count": tool_call_count
                }
            )
        return {'status': 'inserted', 'id': new_id}



def insert_jsonl_to_mongodb(file_path, mongo_uri, db_name, collection_name, batch_size=1000):
    """
    Inserts JSONL file data into a MongoDB collection with error handling.
    
    Args:
        file_path: Path to the JSONL file
        mongo_uri: MongoDB connection URI
        db_name: Target database name
        collection_name: Target collection name
        batch_size: Number of documents to insert per batch (default=1000)
    """

    contents = parse_results(file_path)
    passed_lines, passed_hashes, passed_with_errors_or_skipped_hashes = get_passed(contents) 

    client = None
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        batch = []
        inserted_count = 0
        updated_count = 0
        total_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                try:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Parse JSON and add to batch
                    doc = json.loads(line)
                    id = hashlib.md5(doc['problem_statement'].encode()).hexdigest()
                    doc["problem_statement_hash"] = id
                    if id in passed_hashes:
                        doc["passed"] = True
                        if id in passed_with_errors_or_skipped_hashes:
                            doc["passed_with_errors_or_skipped_hashes"] = True
                        else:
                            doc["passed_with_errors_or_skipped_hashes"] = False
                    else:
                        doc["passed"] = False
                        doc["passed_with_errors_or_skipped_hashes"] = False
                    res = upsert_dict_to_gridfs(db,doc)
                    if res['status'] == 'inserted':
                        inserted_count += 1
                    elif res['status'] == 'updated':
                        updated_count += 1
                    else:
                        raise
                    total_count += 1      
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON on line {line_num}: {e}")
                except PyMongoError as e:
                    print(f"MongoDB error on line {line_num}: {e}")
        # Insert remaining documents in final batch
        # if batch:
        #     result = collection.insert_many(batch)
        #     inserted_count += len(result.inserted_ids)
        #     batch_count += 1
        #     print(f"Inserted final batch: {len(result.inserted_ids)} documents")
        
        print(f"TOTAL INSERTED: {inserted_count} documents of {total_count} total")
        print(f"TOTAL UPDATED: {updated_count} documents of {total_count} total")
        
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        if client:
            client.close()

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
    output_f = open(output_file_name,"w")
    for line in input_f:
        line_trace = create_message_trace(json.loads(line))
        output_f.write(json.dumps(line_trace)+'\n')
        upload_to_mongo(line_trace)
    print("甘肃农业不发达 我们要去支援他")

def upload_to_mongo(message_dict: dict):
    collection.replace_one(
        {"problem_statement_hash": message_dict["problem_statement_hash"]}, message_dict, upsert=True
    )

input_file_name = "TRACEGEN.jsonl"
output_file_name = "qwen_traces2.jsonl"
insert_jsonl_to_mongodb(
    file_path="TRACEGEN.jsonl",
    mongo_uri = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@10.10.100.43:26969/",
    db_name="r2e_traces",
    collection_name="qwen_traces"
)
print("Generating traces...")
run_trace_farmer_for_all(input_file_name, output_file_name)
