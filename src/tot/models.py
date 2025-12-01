import os
import openai
import backoff 

completion_tokens = prompt_tokens = 0

api_key = os.getenv("OPENAI_API_KEY", "")
if api_key != "":
    openai.api_key = api_key
else:
    print("Warning: OPENAI_API_KEY is not set")
    
api_base = os.getenv("OPENAI_API_BASE", "")
if api_base != "":
    print("Warning: OPENAI_API_BASE is set to {}".format(api_base))
    openai.api_base = api_base

# 备用 API 配置
backup_api_key = os.getenv("BACKUP_OPENAI_API_KEY", "")
backup_api_base = os.getenv("BACKUP_OPENAI_API_BASE", "")

@backoff.on_exception(backoff.expo, openai.error.OpenAIError)
def completions_with_backoff(**kwargs):
    try:
        return openai.ChatCompletion.create(**kwargs)
    except openai.error.APIError as e:
        error_message = str(e)
        # 检查是否是 token 限制错误
        if "tokens_limit_reached" in error_message or "Request body too large" in error_message:
            if backup_api_key and backup_api_base:
                print(f"⚠️  遇到 token 限制错误，切换到备用 API")
                print(f"   备用 API Base: {backup_api_base}")
                
                # 保存原始配置
                original_api_key = openai.api_key
                original_api_base = openai.api_base
                
                try:
                    # 切换到备用 API
                    openai.api_key = backup_api_key
                    openai.api_base = backup_api_base
                    
                    result = openai.ChatCompletion.create(**kwargs)
                    print("✓ 使用备用 API 成功")
                    return result
                finally:
                    # 恢复原始配置
                    openai.api_key = original_api_key
                    openai.api_base = original_api_base
            else:
                print("⚠️  遇到 token 限制错误，但未配置备用 API")
                print("   请设置环境变量: BACKUP_OPENAI_API_KEY 和 BACKUP_OPENAI_API_BASE")
        raise

def gpt(prompt, model="gpt-4", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)
    
def chatgpt(messages, model="gpt-4", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens
    outputs = []
    while n > 0:
        cnt = min(n, 20)
        n -= cnt
        res = completions_with_backoff(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, n=cnt, stop=stop)
        outputs.extend([choice.message.content for choice in res.choices])
        # log completion tokens
        completion_tokens += res.usage.completion_tokens
        prompt_tokens += res.usage.prompt_tokens
    return outputs
    
def gpt_usage(backend="gpt-4"):
    global completion_tokens, prompt_tokens
    if backend == "gpt-4":
        cost = completion_tokens / 1000 * 0.06 + prompt_tokens / 1000 * 0.03
    elif backend == "gpt-3.5-turbo":
        cost = completion_tokens / 1000 * 0.002 + prompt_tokens / 1000 * 0.0015
    elif backend == "gpt-4o":
        cost = completion_tokens / 1000 * 0.00250 + prompt_tokens / 1000 * 0.01
    return {"completion_tokens": completion_tokens, "prompt_tokens": prompt_tokens, "cost": cost}
