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
    except openai.error.OpenAIError as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        # 对所有 OpenAI 错误都尝试使用备用 API
        if backup_api_key and backup_api_base:
            print(f"⚠️  遇到 API 错误 ({error_type})，切换到备用 API")
            print(f"   错误信息: {error_message[:200]}...")
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
            except Exception as backup_error:
                print(f"✗ 备用 API 也失败: {str(backup_error)[:200]}")
                raise e  # 抛出原始错误
            finally:
                # 恢复原始配置
                openai.api_key = original_api_key
                openai.api_base = original_api_base
        else:
            print(f"⚠️  遇到 API 错误 ({error_type})，但未配置备用 API")
            print(f"   错误信息: {error_message[:200]}...")
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
        
        # 处理不同的响应格式
        for choice in res.choices:
            try:
                # 尝试标准的 ChatCompletion 格式
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                # 尝试旧版 Completion 格式
                elif hasattr(choice, 'text'):
                    content = choice.text
                # 尝试字典格式
                elif isinstance(choice, dict):
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                    elif 'text' in choice:
                        content = choice['text']
                    else:
                        print(f"⚠️  未知的响应格式，choice keys: {choice.keys()}")
                        print(f"   choice 内容: {choice}")
                        content = str(choice)
                else:
                    print(f"⚠️  未知的 choice 类型: {type(choice)}")
                    print(f"   choice 内容: {choice}")
                    content = str(choice)
                
                outputs.append(content)
            except Exception as e:
                print(f"⚠️  解析响应内容时出错: {e}")
                print(f"   choice 类型: {type(choice)}")
                print(f"   choice 内容: {choice}")
                # 尝试直接转换为字符串
                outputs.append(str(choice))
        
        # log completion tokens
        if hasattr(res, 'usage'):
            completion_tokens += res.usage.completion_tokens
            prompt_tokens += res.usage.prompt_tokens
        elif isinstance(res, dict) and 'usage' in res:
            completion_tokens += res['usage']['completion_tokens']
            prompt_tokens += res['usage']['prompt_tokens']
    
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
