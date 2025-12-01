import os
import re
import json
import tempfile
import contextlib
import signal
from typing import Optional
from tot.tasks.base import Task, DATA_PATH
from tot.prompts.code import (
    function_standard_prompt,
    function_cot_prompt,
    function_h_cot_prompt,
    script_standard_prompt,
    script_cot_prompt,
    vote_prompt,
    value_prompt,
)


_CODE_DATASET_DEFAULT = 'mbppplus.jsonl'

def _load_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return data

class CodeTask(Task):
    """Code generation + functional correctness task supporting multiple datasets.
    Each record must contain: task_id, prompt, public_test_cases, entry_point.
    """
    def __init__(self, dataset_file: Optional[str] = None):
        super().__init__()
        if dataset_file is None:
            dataset_file = os.environ.get('CODE_DATASET', _CODE_DATASET_DEFAULT)
        path = os.path.join(DATA_PATH, 'code', dataset_file)
        self.data = _load_jsonl(path)
        self.steps = 2  # step0: 生成思路/框架, step1: 完成实现
        self.stops = ['\n# Implementation:\n', None]  # step0 在此停止，step1 继续
        self._ctx = None  # 保存当前样例上下文，供 prompt wrapper 使用

    def __len__(self) -> int:
        return len(self.data)

    def get_input(self, idx: int) -> str:
        """
        根据数据集结构，动态构造用于代码生成的输入提示。
        - mbppplus / humanevalplus: 使用 task_id 作为题目标识；要求生成代码以 entry_point 指定的函数名开始；将 public_test_cases 作为参考。
        - lcb / code_contests: 使用 question_id 作为题目标识；需要生成完整可执行脚本；将 public_test_cases 的 stdin/output 作为参考。
        """
        item = self.data[idx]
        dataset_file = os.environ.get('CODE_DATASET', _CODE_DATASET_DEFAULT)
        ds = os.path.basename(dataset_file)

        if ds in ('mbppplus.jsonl', 'humanevalplus.jsonl'):
            mode = 'func'
            task_id = item.get('task_id')
            entry_point = item.get('entry_point')
            problem = item.get('prompt', '')
            public_tests = item.get('public_test_cases', [])
            tests_text = '\n'.join([f'- {tc}' for tc in public_tests])
            meta = f"任务ID: {task_id}"
        elif ds in ('lcb.jsonl', 'code_contests.jsonl'):
            mode = 'script'
            if item.get('starter_code'):  # lcb dataset with non-empty starter_code
                entry_point = item.get('starter_code', '')
                mode = 'func_hs'  # treat as func task
            task_id = item.get('question_id') or item.get('task_id')
            problem = item.get('question_content') or item.get('prompt', '')
            public_tests = item.get('public_test_cases', [])
            tests_text = '\n'.join([str(public_tests)]) if isinstance(public_tests, (dict, list)) else str(public_tests)
            meta = f"题目ID: {task_id}"
        else:
            # 兜底：尽量返回原始 prompt，最小可用
            mode = 'func'
            task_id = item.get('task_id') or item.get('question_id')
            problem = item.get('prompt', '')
            entry_point = item.get('entry_point', '')
            tests_text = ''
            meta = f"任务ID: {task_id}" if task_id else ''

        # 保存上下文，供 wrapper 使用
        self._ctx = {
            'mode': mode,  # 'func' or 'script'
            'task_id': task_id,
            'problem': problem,
            'entry_point': entry_point or '',
            'tests_text': tests_text,
            'meta': meta,
        }
        # 让 x=问题本身，和 text 任务一致；具体模板由 wrapper 选择
        return problem

    # ---------------- Output-only logging (no testing) -----------------
    def test_output(self, idx: int, output: str):
        item = self.data[idx]
        dataset_file = os.environ.get('CODE_DATASET', _CODE_DATASET_DEFAULT)
        ds = os.path.basename(dataset_file)
        # 不同数据集的 task_id 字段名不同
        task_id = item.get('question_id') or item.get('task_id')

        entry_point = self._ctx.get('entry_point') if self._ctx else None
        
        # 提取 Implementation 部分（类似 text.py 的 split('Passage:\n')[-1]）
        if '# Implementation:' in output:
            output = output.split('# Implementation:')[-1].strip()

        code = self._extract_function_code(output, entry_point)
        info = {
            'task_id': task_id,
            'code': code,
        }
        return info

    @staticmethod
    def _extract_function_code(output: str, entry_point: Optional[str]) -> str:
        """
        规范化提取：
        - 去除 Markdown 代码块围栏（``` 或 ``````python）。
        - 只保留首次出现的 `def <entry_point>(...)` 起始的函数实现块。
        - 函数块结束依据：
          1) 下一次出现新的顶层 `def ` 或 `class `；
          2) 文件结束。
        若未提供 entry_point，则返回去围栏后的整体代码。
        """
        # 1) 去除常见 Markdown 围栏
        cleaned = re.sub(r"```+\w*\n", "", output)  # 开始围栏如 ```python 或 ``````python
        cleaned = re.sub(r"\n```+\s*$", "\n", cleaned)  # 结束围栏

        if not entry_point:
            return cleaned.strip()

        lines = cleaned.splitlines()
        start_idx = None
        # 2) 找到首次出现的入口函数定义
        entry_def_pattern = re.compile(rf"^\s*def\s+{re.escape(entry_point)}\s*\(")
        for i, line in enumerate(lines):
            if entry_def_pattern.search(line):
                start_idx = i
                break

        if start_idx is None:
            return cleaned.strip()

        # 3) 从 start_idx 开始，收集到下一个顶层定义或文件结束
        collected = [lines[start_idx]]
        for j in range(start_idx + 1, len(lines)):
            line = lines[j]
            # 顶层定义：行首（非缩进）出现 def/class
            if re.match(r"^def\s+|^class\s+", line):
                break
            collected.append(line)

        return "\n".join(collected).strip()

    # No testing helpers needed; removed.

    # ---------------- Prompts -----------------
    @staticmethod
    def _prompt_func(task_id: str, problem: str, entry_point: Optional[str], public_tests: list) -> str:
        """
        面向函数式题目的提示（mbppplus / humanevalplus）：
        - 要求生成的代码以 entry_point 指定的函数名开始；
        - 将公开测试样例作为参考输入，帮助模型把握函数签名与行为；
        - 其余说明由 prompts/code.py 中的模板填充。
        """
        tests_text = '\n'.join([f'- {tc}' for tc in public_tests])
        # 已由 wrapper 统一处理，此处保留以兼容旧调用（不再使用）
        from tot.prompts.code import function_standard_prompt
        return function_standard_prompt.format(
            input=problem,
            meta=f"任务ID: {task_id}",
            entry_point=entry_point or '',
            tests=tests_text
        )

    @staticmethod
    def _prompt_script(task_id: str, problem: str, public_tests: list) -> str:
        """
        面向脚本式题目的提示（lcb / code_contests）：
        - 生成一个可直接运行的 Python 脚本（包含 main / 输入输出处理）；
        - 提供公开测试的 stdin/output 参考，方便模型对 IO 格式进行对齐。
        """
        tests_text = '\n'.join([str(public_tests)]) if isinstance(public_tests, (dict, list)) else str(public_tests)
        # 已由 wrapper 统一处理，此处保留以兼容旧调用（不再使用）
        from tot.prompts.code import script_cot_prompt
        return script_cot_prompt.format(
            input=problem,
            meta=f"题目ID: {task_id}",
            entry_point='',
            tests=tests_text
        )
    def standard_prompt_wrap(self, x: str, y: str = '') -> str:
        # 根据当前样例类型选择 standard 模板
        ctx = self._ctx or {}
        mode = ctx.get('mode', 'func')
        tpl = function_standard_prompt if mode == 'func' else script_standard_prompt
        prompt = tpl.format(
            input=ctx.get('problem', x),
            meta=ctx.get('meta', ''),
            entry_point=ctx.get('entry_point', ''),
            tests=ctx.get('tests_text', ''),
        )
        return prompt + y

    def cot_prompt_wrap(self, x: str, y: str = '') -> str:
        # 根据当前样例类型选择 cot 模板
        ctx = self._ctx or {}
        mode = ctx.get('mode', 'func')
        if mode == 'func':
            tpl = function_cot_prompt
        elif mode == 'func_h':
            tpl = function_h_cot_prompt  # 可扩展为专门的 func_h cot 模板
        else:
            tpl = script_cot_prompt
        prompt = tpl.format(
            input=ctx.get('problem', x),
            # meta=ctx.get('meta', ''),
            entry_point=ctx.get('entry_point', ''),
            tests=ctx.get('tests_text', ''),
        )
        return prompt + y

    def vote_prompt_wrap(self, x: str, ys: list) -> str:
        # 评审时提供更完整的题目信息
        ctx = self._ctx or {}
        enriched_input = f"{ctx.get('meta','')}\n{ctx.get('problem', x)}"
        if ctx.get('entry_point'):
            enriched_input += f"\n函数入口: {ctx['entry_point']}"
        if ctx.get('tests_text'):
            enriched_input += f"\n参考测试:\n{ctx['tests_text']}"
        body = []
        for i, cand in enumerate(ys, 1):
            body.append(f'Choice {i}:\n{cand}\n')
        return vote_prompt.format(input=enriched_input, candidates=''.join(body))

    @staticmethod
    def vote_outputs_unwrap(vote_outputs: list, n_candidates: int) -> list:
        scores = [0] * n_candidates
        for vote in vote_outputs:
            # 优先匹配 "best choice is X" 格式
            m = re.search(r'best\s+choice\s+is\s+(\d+)', vote, re.IGNORECASE)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < n_candidates:
                    scores[idx] += 1
            else:
                # 降级：提取第一个数字
                m2 = re.search(r'(\d+)', vote)
                if m2:
                    idx = int(m2.group(1)) - 1
                    if 0 <= idx < n_candidates:
                        scores[idx] += 1
        return scores

    def value_prompt_wrap(self, x: str, y: str) -> str:
        ctx = self._ctx or {}
        enriched_input = f"{ctx.get('meta','')}\n{ctx.get('problem', x)}"
        if ctx.get('entry_point'):
            enriched_input += f"\n函数入口: {ctx['entry_point']}"
        if ctx.get('tests_text'):
            enriched_input += f"\n参考测试:\n{ctx['tests_text']}"
        return value_prompt.format(input=enriched_input, output=y)

    @staticmethod
    def value_outputs_unwrap(x: str, y: str, value_outputs: list) -> float:
        # Parse first integer 1-10 else default 5
        vals = []
        for out in value_outputs:
            m = re.search(r'(10|[1-9])', out)
            if m:
                vals.append(int(m.group(1)))
        return sum(vals) / len(vals) if vals else 5.0
    