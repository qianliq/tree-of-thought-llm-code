import os
from openai import OpenAI, AzureOpenAI
import backoff 

completion_tokens = prompt_tokens = 0

api_key = os.getenv("OPENAI_API_KEY", "")
api_base = os.getenv("OPENAI_API_BASE", "")

# 初始化主 OpenAI 客户端
if api_key:
    client = OpenAI(
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    if api_base:
        print("Warning: OPENAI_API_BASE is set to {}".format(api_base))
else:
    print("Warning: OPENAI_API_KEY is not set")
    client = None

# 备用 API 配置
backup_api_key = os.getenv("BACKUP_OPENAI_API_KEY", "")
backup_api_base = os.getenv("BACKUP_OPENAI_API_BASE", "")

# 初始化备用 OpenAI 客户端
if backup_api_key and backup_api_base:
    backup_client = OpenAI(
        api_key=backup_api_key,
        base_url=backup_api_base
    )
else:
    backup_client = None

@backoff.on_exception(backoff.expo, Exception)
def completions_with_backoff(**kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        # 对所有错误都尝试使用备用 API
        if backup_client:
            print(f"⚠️  遇到 API 错误 ({error_type})，切换到备用 API")
            print(f"   错误信息: {error_message[:200]}...")
            print(f"   备用 API Base: {backup_api_base}")
            
            try:
                result = backup_client.chat.completions.create(**kwargs)
                print("✓ 使用备用 API 成功")
                return result
            except Exception as backup_error:
                print(f"✗ 备用 API 也失败: {str(backup_error)[:200]}")
                raise e  # 抛出原始错误
        else:
            print(f"⚠️  遇到 API 错误 ({error_type})，但未配置备用 API")
            print(f"   错误信息: {error_message[:200]}...")
            print("   请设置环境变量: BACKUP_OPENAI_API_KEY 和 BACKUP_OPENAI_API_BASE")
            raise

def gpt(prompt, model="gpt-4", temperature=0.7, max_tokens=8000, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)
    
def chatgpt(messages, model="gpt-4", temperature=0.7, max_tokens=8000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens
    outputs = []
    while n > 0:
        # 某些 API（如阿里云）限制 n 的最大值为 4
        cnt = min(n, 4)
        n -= cnt
        res = completions_with_backoff(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, n=cnt, stop=stop)
        
        # 记录本次调用的 token 使用情况
        current_prompt_tokens = 0
        current_completion_tokens = 0
        if hasattr(res, 'usage') and res.usage:
            current_prompt_tokens = res.usage.prompt_tokens
            current_completion_tokens = res.usage.completion_tokens
            total_tokens = res.usage.total_tokens
        else:
            total_tokens = 0
        
        # 打印 token 使用情况
        if total_tokens > 0:
            print(f"📊 Token 使用: prompt={current_prompt_tokens}, completion={current_completion_tokens}, total={total_tokens}")
        
        # 检查是否被截断
        truncated_count = 0
        for choice in res.choices:
            if choice.finish_reason == 'length':
                truncated_count += 1
        
        if truncated_count > 0:
            print(f"⚠️  警告: {truncated_count}/{cnt} 个响应因达到 max_tokens 限制而被截断 (max_tokens={max_tokens})")
        
        # 新版 SDK 使用统一的响应格式
        for choice in res.choices:
            try:
                content = choice.message.content
                if content is not None:
                    outputs.append(content)
                else:
                    print(f"⚠️  警告: choice.message.content 为 None")
            except Exception as e:
                print(f"⚠️  解析响应内容时出错: {e}")
                print(f"   choice 类型: {type(choice)}")
                print(f"   choice 内容: {choice}")
        
        # log completion tokens
        completion_tokens += current_completion_tokens
        prompt_tokens += current_prompt_tokens
    
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
