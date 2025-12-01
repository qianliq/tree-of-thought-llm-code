#!/usr/bin/env python3
"""
重命名 JSONL 文件中的字段
用法: python rename_field.py <input_file> <old_field> <new_field> [output_file]
"""

import json
import sys
import os


def rename_field_in_jsonl(input_file: str, old_field: str, new_field: str, output_file: str):
    """处理 JSONL 文件，重命名指定字段"""
    processed_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # 重命名字段
                if old_field in data:
                    data[new_field] = data.pop(old_field)
                    processed_count += 1
                
                # 写入处理后的记录
                json.dump(data, f_out, ensure_ascii=False)
                f_out.write('\n')
                
            except json.JSONDecodeError as e:
                print(f"警告: 第 {line_num} 行 JSON 解析失败: {e}", file=sys.stderr)
                continue
    
    print(f"处理完成！共重命名 {processed_count} 个字段")
    print(f"字段: '{old_field}' -> '{new_field}'")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")


def main():
    if len(sys.argv) < 4:
        print("用法: python rename_field.py <input_file> <old_field> <new_field> [output_file]")
        print("示例: python rename_field.py input.jsonl code solution output.jsonl")
        print("      python rename_field.py input.jsonl code solution  # 自动生成输出文件名")
        sys.exit(1)
    
    input_file = sys.argv[1]
    old_field = sys.argv[2]
    new_field = sys.argv[3]
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}", file=sys.stderr)
        sys.exit(1)
    
    # 如果没有指定输出文件，自动生成文件名
    if len(sys.argv) >= 5:
        output_file = sys.argv[4]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_renamed{ext}"
    
    # 检查是否会覆盖输入文件
    if os.path.abspath(input_file) == os.path.abspath(output_file):
        print("错误: 输出文件不能与输入文件相同", file=sys.stderr)
        sys.exit(1)
    
    rename_field_in_jsonl(input_file, old_field, new_field, output_file)


if __name__ == '__main__':
    main()
