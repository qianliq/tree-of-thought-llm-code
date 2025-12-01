#!/usr/bin/env python3
"""
为 JSONL 文件中的所有代码添加标准导入头
用法: python add_imports.py <input_file> [output_file]
"""

import json
import sys
import os

import_helper = """from string import *
from re import *
from datetime import *
from collections import *
from heapq import *
from bisect import *
from copy import *
from math import *
from random import *
from statistics import *
from itertools import *
from functools import *
from operator import *
from io import *
from sys import *
from json import *
from builtins import *
from typing import *
import string
import re
import datetime
import collections
import heapq
import bisect
import copy
import math
import random
import statistics
import itertools
import functools
import operator
import io
import sys
import json
sys.setrecursionlimit(50000)
"""


def add_imports_to_code(code: str) -> str:
    """为代码添加 import_helper 前缀"""
    if not code:
        return code
    return import_helper + code


def process_jsonl(input_file: str, output_file: str):
    """处理 JSONL 文件，为所有 code 字段添加导入"""
    processed_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # 添加 imports 到 solution 字段
                if 'solution' in data:
                    data['solution'] = add_imports_to_code(data['solution'])
                    processed_count += 1
                
                # 写入处理后的记录
                json.dump(data, f_out, ensure_ascii=False)
                f_out.write('\n')
                
            except json.JSONDecodeError as e:
                print(f"警告: 第 {line_num} 行 JSON 解析失败: {e}", file=sys.stderr)
                continue
    
    print(f"处理完成！共处理 {processed_count} 条记录")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: python add_imports.py <input_file> [output_file]")
        print("示例: python add_imports.py input.jsonl output.jsonl")
        print("      python add_imports.py input.jsonl  # 会创建 input_with_imports.jsonl")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}", file=sys.stderr)
        sys.exit(1)
    
    # 如果没有指定输出文件，自动生成文件名
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_with_imports{ext}"
    
    # 检查是否会覆盖输入文件
    if os.path.abspath(input_file) == os.path.abspath(output_file):
        print("错误: 输出文件不能与输入文件相同", file=sys.stderr)
        sys.exit(1)
    
    process_jsonl(input_file, output_file)


if __name__ == '__main__':
    main()
