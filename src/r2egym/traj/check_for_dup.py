import sys

def find_duplicate_hashes(data):
    hash_count = {}
    lines = data.splitlines()
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        parts = stripped_line.split()
        if parts:
            hash_val = parts[0]
            hash_count[hash_val] = hash_count.get(hash_val, 0) + 1
    
    duplicates = [hash_val for hash_val, count in hash_count.items() if count > 1]
    return duplicates

if __name__ == '__main__':
    with open("passed_lines.txt") as f:
        data = f.read()
    duplicates = find_duplicate_hashes(data)

    if duplicates:
        print("Duplicate hashes found:")
        for dup in duplicates:
            print(dup)
    else:
        print("No duplicate hashes found.")