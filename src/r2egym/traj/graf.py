from pymongo import MongoClient
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import os  # Import os module for directory handling

# Connect to MongoDB
mongo_uri = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@10.10.100.43:26969/"
db_name = "swe_gym_plus"
collection_name = "qwen_traces.files"
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_name]

# Extract data from MongoDB
data = []
for doc in collection.find({"metadata.passed": True}, {"metadata": 1}):
    meta = doc.get("metadata", {})
    data.append({
        "total_prompt_tokens": meta.get("total_prompt_tokens"),
        "total_tokens": meta.get("total_tokens"),
        "num_steps": meta.get("num_steps"),
        "max_tokens": meta.get("max_tokens")
    })
print(len(data))
# Convert to DataFrame
df = pd.DataFrame(data)

# Create graphs directory if not exists
os.makedirs('graphs', exist_ok=True)

# Set up the plot
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Distribution of Metadata Fields (Passed Only)', fontsize=16)

# Plot each distribution
sns.histplot(df['total_prompt_tokens'].dropna(), kde=True, ax=axes[0, 0], bins=30)
axes[0, 0].set_title('Total Prompt Tokens')
axes[0, 0].set_xlabel('Token Count')

sns.histplot(df['total_tokens'].dropna(), kde=True, ax=axes[0, 1], bins=30)
axes[0, 1].set_title('Total Tokens')
axes[0, 1].set_xlabel('Token Count')

sns.histplot(df['num_steps'].dropna(), kde=True, ax=axes[1, 0], bins=30)
axes[1, 0].set_title('Number of Steps')
axes[1, 0].set_xlabel('Steps')

sns.histplot(df['max_tokens'].dropna(), kde=True, ax=axes[1, 1], bins=30)
axes[1, 1].set_title('Max Tokens')
axes[1, 1].set_xlabel('Largest Step Token Count')

# Adjust layout and save combined figure
plt.tight_layout(rect=[0, 0, 1, 0.96])  # Make space for suptitle
plt.savefig('graphs/combined_distributions.png', dpi=300)
plt.close(fig)  # Close the combined figure

# Save individual plots
def save_individual_plot(column, title, xlabel):
    plt.figure(figsize=(8, 6))
    sns.histplot(df[column].dropna(), kde=True, bins=30)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(f'graphs/{column}.png', dpi=300)
    plt.close()

# Save each metric individually
save_individual_plot('total_prompt_tokens', 'Total Prompt Tokens', 'Token Count')
save_individual_plot('total_tokens', 'Total Tokens', 'Token Count')
save_individual_plot('num_steps', 'Number of Steps', 'Steps')
save_individual_plot('max_tokens', 'Max Tokens', 'Token Limit')