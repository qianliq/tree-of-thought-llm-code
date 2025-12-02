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

def gpt(prompt, model="gpt-4", temperature=0.7, max_tokens=8000, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)
    
def chatgpt(messages, model="gpt-4", temperature=0.7, max_tokens=8000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens
    outputs = []
    while n > 0:
        cnt = min(n, 20)
        n -= cnt
        res = completions_with_backoff(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, n=cnt, stop=stop)
        
        # 记录本次调用的 token 使用情况
        current_prompt_tokens = 0
        current_completion_tokens = 0
        if hasattr(res, 'usage'):
            current_prompt_tokens = res.usage.prompt_tokens
            current_completion_tokens = res.usage.completion_tokens
            total_tokens = res.usage.total_tokens if hasattr(res.usage, 'total_tokens') else current_prompt_tokens + current_completion_tokens
        elif isinstance(res, dict) and 'usage' in res:
            current_prompt_tokens = res['usage']['prompt_tokens']
            current_completion_tokens = res['usage']['completion_tokens']
            total_tokens = res['usage'].get('total_tokens', current_prompt_tokens + current_completion_tokens)
        else:
            total_tokens = 0
        
        # 打印 token 使用情况
        if total_tokens > 0:
            print(f"📊 Token 使用: prompt={current_prompt_tokens}, completion={current_completion_tokens}, total={total_tokens}")
        
        # 检查是否被截断
        truncated_count = 0
        for choice in res.choices:
            finish_reason = None
            if hasattr(choice, 'finish_reason'):
                finish_reason = choice.finish_reason
            elif isinstance(choice, dict) and 'finish_reason' in choice:
                finish_reason = choice['finish_reason']
            
            if finish_reason == 'length':
                truncated_count += 1
        
        if truncated_count > 0:
            print(f"⚠️  警告: {truncated_count}/{cnt} 个响应因达到 max_tokens 限制而被截断 (max_tokens={max_tokens})")
        
        # 处理不同的响应格式
        parse_failed = False
        for choice in res.choices:
            try:
                content = None
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
                        parse_failed = True
                else:
                    print(f"⚠️  未知的 choice 类型: {type(choice)}")
                    print(f"   choice 内容: {choice}")
                    parse_failed = True
                
                if content is not None:
                    outputs.append(content)
                else:
                    parse_failed = True
                    
            except Exception as e:
                print(f"⚠️  解析响应内容时出错: {e}")
                print(f"   choice 类型: {type(choice)}")
                print(f"   choice 内容: {choice}")
                parse_failed = True
        
        # 如果解析失败，尝试使用备用 API
        if parse_failed and backup_api_key and backup_api_base:
            print(f"⚠️  响应格式解析失败，尝试使用备用 API")
            print(f"   备用 API Base: {backup_api_base}")
            
            # 保存原始配置
            original_api_key = openai.api_key
            original_api_base = openai.api_base
            
            try:
                # 切换到备用 API
                openai.api_key = backup_api_key
                openai.api_base = backup_api_base
                
                # 清空之前的输出并重新请求
                outputs = []
                backup_res = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, n=cnt, stop=stop)
                
                # 解析备用 API 的响应
                for choice in backup_res.choices:
                    if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                        outputs.append(choice.message.content)
                    elif hasattr(choice, 'text'):
                        outputs.append(choice.text)
                    elif isinstance(choice, dict):
                        if 'message' in choice and 'content' in choice['message']:
                            outputs.append(choice['message']['content'])
                        elif 'text' in choice:
                            outputs.append(choice['text'])
                
                res = backup_res  # 使用备用 API 的响应来记录 token
                print(f"✓ 使用备用 API 成功，获得 {len(outputs)} 个响应")
                
                # 重新计算备用 API 的 token 使用情况
                if hasattr(res, 'usage'):
                    current_prompt_tokens = res.usage.prompt_tokens
                    current_completion_tokens = res.usage.completion_tokens
                elif isinstance(res, dict) and 'usage' in res:
                    current_prompt_tokens = res['usage']['prompt_tokens']
                    current_completion_tokens = res['usage']['completion_tokens']
                
            except Exception as backup_error:
                print(f"✗ 备用 API 也失败: {str(backup_error)[:200]}")
                # 如果备用 API 也失败，使用原始响应的字符串形式
                outputs = [str(choice) for choice in res.choices]
            finally:
                # 恢复原始配置
                openai.api_key = original_api_key
                openai.api_base = original_api_base
        elif parse_failed:
            print("⚠️  响应格式解析失败，但未配置备用 API")
            print("   请设置环境变量: BACKUP_OPENAI_API_KEY 和 BACKUP_OPENAI_API_BASE")
            # 使用字符串形式作为后备
            outputs.extend([str(choice) for choice in res.choices if choice not in [o for o in outputs]])
        
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
