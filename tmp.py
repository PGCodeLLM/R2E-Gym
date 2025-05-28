# from litellm import model_list
from litellm import completion
# print(model_list(api_base="https://api.deepseek.com", api_key="sk-8b2e0e39b7a642ca819c752c95199f70"))
# print(completion.available_models)

response = completion(
    model="deepseek/deepseek-chat",  # ✅ try known valid model
    messages=[{"role": "user", "content": "Hello!"}],
    api_key="sk-8b2e0e39b7a642ca819c752c95199f70",
    api_base="https://api.deepseek.com",  # or /v1 depending on API
)
print(response)