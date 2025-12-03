#!/usr/bin/env python3
"""
合并多个 JSONL 结果文件

使用方法:
    python merge_results.py --dataset data.jsonl --results result1.jsonl result2.jsonl result3.jsonl --output merged.jsonl
    python merge_results.py --dataset data.jsonl --results result*.jsonl --output merged.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict


def get_task_id(item: dict) -> str:
    """
    从数据项中提取任务ID
    优先查找 task_id，如果没有则查找 question_id
    
    参数:
        item: 数据项字典
    
    返回:
        任务ID字符串
    """
    if 'task_id' in item:
        return str(item['task_id'])
    elif 'question_id' in item:
        return str(item['question_id'])
    else:
        raise KeyError(f"数据项中没有找到 'task_id' 或 'question_id' 字段: {list(item.keys())}")


def load_jsonl(file_path: str) -> List[dict]:
    """
    加载 JSONL 文件
    
    参数:
        file_path: 文件路径
    
    返回:
        数据项列表
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️  警告: {file_path} 第 {line_num} 行 JSON 解析失败: {e}")
    return data


def save_jsonl(data: List[dict], file_path: str):
    """
    保存为 JSONL 文件
    
    参数:
        data: 数据项列表
        file_path: 输出文件路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def merge_results(dataset_path: str, result_paths: List[str], output_path: str, verbose: bool = True):
    """
    合并多个结果文件
    
    参数:
        dataset_path: 数据集文件路径
        result_paths: 结果文件路径列表
        output_path: 输出文件路径
        verbose: 是否显示详细信息
    """
    # 加载数据集
    if verbose:
        print(f"📖 加载数据集: {dataset_path}")
    dataset = load_jsonl(dataset_path)
    
    if not dataset:
        print("❌ 错误: 数据集为空")
        sys.exit(1)
    
    # 获取数据集中的所有任务ID（按顺序）
    dataset_task_ids = []
    dataset_id_field = None
    
    for item in dataset:
        try:
            task_id = get_task_id(item)
            dataset_task_ids.append(task_id)
            if dataset_id_field is None:
                dataset_id_field = 'task_id' if 'task_id' in item else 'question_id'
        except KeyError as e:
            print(f"❌ 错误: {e}")
            sys.exit(1)
    
    if verbose:
        print(f"✓ 数据集包含 {len(dataset_task_ids)} 个任务 (ID 字段: {dataset_id_field})")
    
    # 加载所有结果文件
    results_by_task_id = defaultdict(list)
    all_result_task_ids = set()
    
    for result_path in result_paths:
        if verbose:
            print(f"\n📖 加载结果文件: {result_path}")
        
        results = load_jsonl(result_path)
        
        if not results:
            if verbose:
                print(f"   ⚠️  警告: 结果文件为空，跳过")
            continue
        
        # 检测结果文件使用的ID字段
        result_id_field = None
        for item in results:
            try:
                task_id = get_task_id(item)
                result_id_field = 'task_id' if 'task_id' in item else 'question_id'
                break
            except KeyError:
                continue
        
        if result_id_field is None:
            print(f"   ⚠️  警告: 结果文件中没有找到有效的任务ID字段，跳过")
            continue
        
        # 收集结果
        file_task_ids = set()
        for item in results:
            try:
                task_id = get_task_id(item)
                results_by_task_id[task_id].append(item)
                file_task_ids.add(task_id)
                all_result_task_ids.add(task_id)
            except KeyError as e:
                if verbose:
                    print(f"   ⚠️  警告: 跳过无效数据项: {e}")
        
        if verbose:
            print(f"   ✓ 包含 {len(file_task_ids)} 个任务的结果")
    
    # 检查覆盖率
    if verbose:
        print(f"\n{'='*80}")
        print("📊 覆盖率分析:")
        print(f"{'='*80}")
    
    dataset_task_id_set = set(dataset_task_ids)
    missing_task_ids = dataset_task_id_set - all_result_task_ids
    extra_task_ids = all_result_task_ids - dataset_task_id_set
    
    coverage = len(all_result_task_ids & dataset_task_id_set) / len(dataset_task_id_set) * 100
    
    if verbose:
        print(f"数据集任务总数: {len(dataset_task_id_set)}")
        print(f"结果文件覆盖: {len(all_result_task_ids & dataset_task_id_set)}")
        print(f"覆盖率: {coverage:.2f}%")
    
    if missing_task_ids:
        print(f"\n⚠️  缺失的任务 ({len(missing_task_ids)} 个):")
        missing_list = sorted(missing_task_ids, key=lambda x: dataset_task_ids.index(x) if x in dataset_task_ids else float('inf'))
        for i, task_id in enumerate(missing_list[:10]):  # 只显示前10个
            idx = dataset_task_ids.index(task_id) if task_id in dataset_task_ids else -1
            print(f"   - {task_id} (索引: {idx})")
        if len(missing_task_ids) > 10:
            print(f"   ... 还有 {len(missing_task_ids) - 10} 个")
    
    if extra_task_ids:
        print(f"\n⚠️  额外的任务 (不在数据集中) ({len(extra_task_ids)} 个):")
        for i, task_id in enumerate(sorted(extra_task_ids)[:10]):  # 只显示前10个
            print(f"   - {task_id}")
        if len(extra_task_ids) > 10:
            print(f"   ... 还有 {len(extra_task_ids) - 10} 个")
    
    # 按数据集顺序合并结果
    if verbose:
        print(f"\n{'='*80}")
        print("🔄 合并结果...")
        print(f"{'='*80}\n")
    
    merged_data = []
    tasks_with_multiple_results = []
    
    for task_id in dataset_task_ids:
        if task_id in results_by_task_id:
            task_results = results_by_task_id[task_id]
            
            if len(task_results) > 1:
                tasks_with_multiple_results.append((task_id, len(task_results)))
                if verbose:
                    print(f"⚠️  任务 {task_id} 有 {len(task_results)} 个结果，使用第一个")
            
            # 使用第一个结果
            merged_data.append(task_results[0])
        else:
            if verbose:
                print(f"⚠️  任务 {task_id} 没有结果，跳过")
    
    if tasks_with_multiple_results and verbose:
        print(f"\n📋 有 {len(tasks_with_multiple_results)} 个任务有多个结果:")
        for task_id, count in tasks_with_multiple_results[:5]:
            print(f"   - {task_id}: {count} 个结果")
        if len(tasks_with_multiple_results) > 5:
            print(f"   ... 还有 {len(tasks_with_multiple_results) - 5} 个")
    
    # 保存合并结果
    if verbose:
        print(f"\n💾 保存合并结果到: {output_path}")
    
    save_jsonl(merged_data, output_path)
    
    if verbose:
        print(f"\n{'='*80}")
        print("✓ 合并完成!")
        print(f"{'='*80}")
        print(f"输入数据集: {len(dataset)} 个任务")
        print(f"输出结果: {len(merged_data)} 个任务")
        print(f"覆盖率: {len(merged_data) / len(dataset) * 100:.2f}%")


def interactive_mode():
    """交互式模式"""
    print(f"{'='*80}")
    print("🔄 合并结果文件 - 交互模式")
    print(f"{'='*80}\n")
    
    # 输入数据集路径
    while True:
        dataset_path = input("📖 请输入数据集文件路径: ").strip()
        # 移除可能的引号
        dataset_path = dataset_path.strip("'\"")
        
        if not dataset_path:
            print("❌ 数据集路径不能为空")
            continue
        
        if not Path(dataset_path).exists():
            print(f"❌ 文件不存在: {dataset_path}")
            continue
        
        break
    
    print(f"✓ 数据集: {dataset_path}\n")
    
    # 选择输入模式
    print("📝 请选择结果文件输入模式:")
    print("   1. 逐个输入文件路径（支持通配符）")
    print("   2. 指定目录（自动收集目录下所有 .jsonl 文件）")
    
    while True:
        mode = input("\n请选择 (1/2): ").strip()
        if mode in ['1', '2']:
            break
        print("❌ 无效选择，请输入 1 或 2")
    
    result_files = []
    
    if mode == '2':
        # 目录模式
        while True:
            result_dir = input("\n📂 请输入结果文件目录: ").strip().strip("'\"")
            
            if not result_dir:
                print("❌ 目录路径不能为空")
                continue
            
            dir_path = Path(result_dir)
            if not dir_path.exists():
                print(f"❌ 目录不存在: {result_dir}")
                continue
            
            if not dir_path.is_dir():
                print(f"❌ 不是有效的目录: {result_dir}")
                continue
            
            break
        
        # 询问是否需要过滤
        print("\n🔍 是否需要过滤文件名？")
        print("   示例: *_lcb_*.jsonl, *humanevalplus*.jsonl")
        pattern = input("   文件模式 (直接回车使用 *.jsonl): ").strip()
        
        if not pattern:
            pattern = "*.jsonl"
        
        # 收集文件
        matches = list(dir_path.glob(pattern))
        if matches:
            result_files = [str(f) for f in matches if f.is_file()]
            print(f"\n✓ 找到 {len(result_files)} 个文件:")
            for i, f in enumerate(result_files[:10], 1):
                print(f"   {i}. {Path(f).name}")
            if len(result_files) > 10:
                print(f"   ... 还有 {len(result_files) - 10} 个文件")
        else:
            print(f"\n❌ 没有找到匹配的文件: {pattern}")
            print("是否继续使用逐个输入模式? (y/n): ", end='')
            if input().strip().lower() == 'y':
                mode = '1'
            else:
                sys.exit(1)
    
    if mode == '1':
        # 逐个输入模式
        print("\n📝 请输入结果文件路径（支持通配符）")
        print("   提示: 每行一个文件路径，输入空行结束\n")
        
        line_num = 1
        
        while True:
            prompt = f"   结果文件 #{line_num}: "
            result_path = input(prompt).strip()
            # 移除可能的引号
            result_path = result_path.strip("'\"")
            
            if not result_path:
                # 空行，结束输入
                if not result_files:
                    print("❌ 至少需要一个结果文件")
                    continue
                break
            
            # 检查是否是绝对路径
            path_obj = Path(result_path)
            if path_obj.is_absolute():
                # 绝对路径，直接检查文件是否存在
                if path_obj.exists():
                    if result_path not in result_files:
                        result_files.append(result_path)
                        print(f"      ✓ 添加: {result_path}")
                    else:
                        print(f"      ⚠️  已存在: {result_path}")
                else:
                    # 可能是绝对路径的通配符，尝试使用父目录进行 glob
                    if '*' in result_path or '?' in result_path:
                        parent = path_obj.parent
                        pattern = path_obj.name
                        matches = list(parent.glob(pattern))
                        if matches:
                            for match in matches:
                                if str(match) not in result_files:
                                    result_files.append(str(match))
                                    print(f"      ✓ 添加: {match}")
                        else:
                            print(f"      ❌ 没有匹配的文件: {result_path}")
                    else:
                        print(f"      ❌ 文件不存在: {result_path}")
                        print("      是否继续添加其他文件? (y/n): ", end='')
                        if input().strip().lower() != 'y':
                            continue
            else:
                # 相对路径，支持通配符
                matches = list(Path('.').glob(result_path))
                if matches:
                    for match in matches:
                        if str(match) not in result_files:
                            result_files.append(str(match))
                            print(f"      ✓ 添加: {match}")
                else:
                    # 不是通配符，直接检查文件
                    if Path(result_path).exists():
                        if result_path not in result_files:
                            result_files.append(result_path)
                            print(f"      ✓ 添加: {result_path}")
                        else:
                            print(f"      ⚠️  已存在: {result_path}")
                    else:
                        print(f"      ❌ 文件不存在: {result_path}")
                        print("      是否继续添加其他文件? (y/n): ", end='')
                        if input().strip().lower() != 'y':
                            continue
            
            line_num += 1
    
    if not result_files:
        print("\n❌ 错误: 没有有效的结果文件")
        sys.exit(1)
    
    # 去重并排序
    result_files = sorted(set(result_files))
    
    # 生成输出文件名：使用第一个结果文件名 + _merged 后缀
    first_result = Path(result_files[0])
    output_path = str(first_result.parent / f"{first_result.stem}_merged{first_result.suffix}")
    
    print(f"\n{'='*80}")
    print("📁 文件信息:")
    print(f"{'='*80}")
    print(f"数据集: {dataset_path}")
    print(f"结果文件 ({len(result_files)} 个):")
    for f in result_files:
        print(f"   - {f}")
    print(f"输出: {output_path}")
    
    # 确认
    print(f"\n是否继续合并? (y/n): ", end='')
    if input().strip().lower() != 'y':
        print("已取消")
        sys.exit(0)
    
    print()
    
    # 执行合并
    merge_results(dataset_path, result_files, output_path, verbose=True)


def main():
    parser = argparse.ArgumentParser(
        description='合并多个 JSONL 结果文件，按数据集顺序输出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 交互模式（默认）
    python merge_results.py
    
    # 命令行模式
    python merge_results.py --dataset data/humanevalplus.jsonl \\
        --results result1.jsonl result2.jsonl result3.jsonl \\
        --output merged.jsonl
    
    # 使用通配符
    python merge_results.py --dataset data/lcb.jsonl \\
        --results logs/code/*_lcb_*.jsonl \\
        --output merged_lcb.jsonl
    
    # 目录模式（自动收集目录下所有 .jsonl 文件）
    python merge_results.py --dataset data/humanevalplus.jsonl \\
        --result-dir logs/code \\
        --output merged.jsonl
    
    # 目录模式 + 模式过滤
    python merge_results.py --dataset data/lcb.jsonl \\
        --result-dir logs/code \\
        --pattern "*_lcb_*.jsonl" \\
        --output merged_lcb.jsonl
    
    # 静默模式
    python merge_results.py --dataset data.jsonl \\
        --results result*.jsonl \\
        --output merged.jsonl \\
        --quiet
        """
    )
    
    parser.add_argument('--dataset', '-d', 
                        help='数据集 JSONL 文件路径')
    parser.add_argument('--results', '-r', nargs='+',
                        help='结果 JSONL 文件路径（可以多个）')
    parser.add_argument('--result-dir', '--dir',
                        help='结果文件所在目录（自动收集该目录下所有 .jsonl 文件）')
    parser.add_argument('--pattern', '-p',
                        help='文件名模式（用于过滤 --result-dir 中的文件，如 "*_lcb_*.jsonl"）')
    parser.add_argument('--output', '-o',
                        help='输出合并后的 JSONL 文件路径')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='静默模式，只显示错误信息')
    
    args = parser.parse_args()
    
    # 如果没有提供参数，进入交互模式
    if not args.dataset or (not args.results and not args.result_dir):
        interactive_mode()
        return
    
    # 命令行模式
    if not args.output:
        print("❌ 错误: 命令行模式需要指定 --output 参数")
        sys.exit(1)
    
    # 检查数据集文件是否存在
    if not Path(args.dataset).exists():
        print(f"❌ 错误: 数据集文件不存在: {args.dataset}")
        sys.exit(1)
    
    # 收集结果文件
    result_files = []
    
    # 如果指定了目录模式
    if args.result_dir:
        result_dir = Path(args.result_dir)
        if not result_dir.exists():
            print(f"❌ 错误: 结果目录不存在: {args.result_dir}")
            sys.exit(1)
        
        if not result_dir.is_dir():
            print(f"❌ 错误: 不是有效的目录: {args.result_dir}")
            sys.exit(1)
        
        # 使用模式过滤，默认为所有 .jsonl 文件
        pattern = args.pattern if args.pattern else "*.jsonl"
        
        if not args.quiet:
            print(f"📂 从目录收集结果文件: {args.result_dir}")
            print(f"   文件模式: {pattern}")
        
        # 收集目录下的所有匹配文件
        matches = list(result_dir.glob(pattern))
        if matches:
            result_files.extend([str(f) for f in matches if f.is_file()])
            if not args.quiet:
                print(f"   找到 {len(result_files)} 个文件")
        else:
            print(f"⚠️  警告: 目录中没有找到匹配的文件: {pattern}")
    
    # 如果指定了具体的结果文件
    if args.results:
        for pattern in args.results:
            matches = list(Path('.').glob(pattern))
            if matches:
                result_files.extend([str(f) for f in matches])
            else:
                # 如果不是通配符，直接添加
                if Path(pattern).exists():
                    result_files.append(pattern)
                else:
                    print(f"⚠️  警告: 结果文件不存在: {pattern}")
    
    if not result_files:
        print(f"❌ 错误: 没有找到任何结果文件")
        sys.exit(1)
    
    # 去重
    result_files = sorted(set(result_files))
    
    if not args.quiet:
        print(f"{'='*80}")
        print("📁 文件信息:")
        print(f"{'='*80}")
        print(f"数据集: {args.dataset}")
        print(f"结果文件 ({len(result_files)} 个):")
        for f in result_files:
            print(f"   - {f}")
        print(f"输出: {args.output}")
        print()
    
    # 合并
    merge_results(args.dataset, result_files, args.output, verbose=not args.quiet)


if __name__ == '__main__':
    main()
