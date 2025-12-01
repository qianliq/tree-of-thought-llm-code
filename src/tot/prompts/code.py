# 提供四套模板：函数式/脚本式 × standard/cot

function_standard_prompt = '''
"""
【函数式题目（standard）】
任务说明:
{meta}

题目内容:
{input}

函数入口（必须使用该函数名，并且函数定义以此开头）：
{entry_point}

参考公开测试（用于帮助理解函数行为；无需在代码中打印）：
{tests}
"""

First, write your approach and key insights as comments.
Your output should be of the following format:

# Approach:
Your approach here.

# Implementation:
```python
Your code here.
```
'''

function_cot_prompt = '''
"""
Problem Description:
{input}

Function Entry Point (must use this function name, and the function definition must start with this):
{entry_point}

Public Test Cases (to help understand function behavior; do not print in code):
{tests}
"""

Let's think step by step. Your output should be of the following format:

# Approach:
Your step-by-step approach here.

# Implementation:
```python
Your code here starting with "def {entry_point}(...):"
```
'''

script_standard_prompt = '''
"""
【脚本式题目（standard）】
题目信息:
{meta}

题目内容:
{input}

参考公开测试（stdin / output 格式）：
{tests}
"""

First, write your approach and algorithm design as comments.
Your output should be of the following format:

# Approach:
Your approach here.

# Implementation:
```python
Your complete Python script here.
```
'''

script_cot_prompt = '''
"""
### Question:
{input}

Public Test Cases (to help understand function behavior; do not print in code):
{tests}
"""

Let's think step by step. Your output should be of the following format:

# Approach:
Your step-by-step approach here.

# Implementation:
## Format:Read the inputs from stdin solve the problem and write the answer to stdout (do not directly test on the sample inputs). Enclose your code within delimiters as follows. Ensure that when the python program runs, it reads the inputs, runs the algorithm and writes output to STDOUT.
```python
Your code here.
```
'''

function_h_cot_prompt = '''
"""
### Question:
{input}

Public Test Cases (to help understand function behavior; do not print in code):
{tests}
"""

Let's think step by step. Your output should be of the following format:

# Approach:
Your step-by-step approach here.

# Implementation:
## Format: You will use the following starter code to write the solution to the problem and enclose your code within delimiters. Do not 
```python
Your code here starting with the starter code:
{entry_point}
```
'''

vote_prompt = '''
Given an instruction and several choices, decide which choice is most promising. Analyze each choice in detail, then conclude in the last line "The best choice is {{s}}", where {{s}} is the integer id of the choice.

Problem:
{input}

Candidate Solutions:
{candidates}

Evaluation Criteria: correctness / readability / efficiency / edge case handling.
'''

value_prompt = '''
Analyze the following solution base on the problem, then at the last line conclude "Thus the solution score is s", where s is an integer from 1 to 10

Problem:
{input}

Solution:
{output}

Suggested scoring dimensions: correctness, efficiency, maintainability, robustness.
'''
