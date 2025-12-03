#!/usr/bin/env python3
"""
并行执行脚本 - 将任务范围拆分到多个子进程中并行执行

使用方法:
    python parallel_run.py scripts/code/cc_bfs.sh --num_workers 4
    python parallel_run.py scripts/code/cc_bfs.sh --num_workers 8 --override_start 0 --override_end 100
"""

import argparse
import subprocess
import os
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
import threading
import time


def parse_shell_script(script_path: str) -> Tuple[List[str], Dict[str, str]]:
    """
    解析 shell 脚本，提取命令和参数
    
    返回:
        (command_parts, params): 命令部分列表和参数字典
    """
    with open(script_path, 'r') as f:
        content = f.read()
    
    # 移除注释和空行，合并多行命令
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # 移除行尾的反斜杠
            line = line.rstrip('\\').strip()
            lines.append(line)
    
    # 合并所有行
    full_command = ' '.join(lines)
    
    # 解析参数
    params = {}
    command_parts = []
    
    parts = full_command.split()
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith('--'):
            # 这是一个参数
            param_name = part
            if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                param_value = parts[i + 1]
                params[param_name] = param_value
                i += 2
            else:
                params[param_name] = ''
                i += 1
        else:
            # 这是命令的一部分
            if part != '${@}':  # 跳过 ${@}
                command_parts.append(part)
            i += 1
    
    return command_parts, params


def split_range(start: int, end: int, num_workers: int) -> List[Tuple[int, int]]:
    """
    将任务范围拆分成 num_workers 个子范围，尽可能均衡分配
    注意: 为了避免跳过索引，使用重叠的范围 (如 0-32, 32-64)
    范围表示为 (start, end]，即不包含 start，包含 end
    
    参数:
        start: 起始索引
        end: 结束索引
        num_workers: 工作线程数
    
    返回:
        [(start1, end1), (start2, end2), ...] 范围列表
        
    示例:
        380 个任务，100 个 worker:
        - 80 个 worker 分配 4 个任务
        - 20 个 worker 分配 3 个任务
    """
    total_tasks = end - start
    
    # 如果任务数少于 worker 数，只使用需要的 worker 数
    if total_tasks <= 0:
        return []
    
    actual_workers = min(num_workers, total_tasks)
    
    # 计算基本任务数和余数
    base_tasks = total_tasks // actual_workers
    remainder = total_tasks % actual_workers
    
    ranges = []
    current_start = start
    
    for i in range(actual_workers):
        # 前 remainder 个 worker 多分配一个任务
        tasks_for_this_worker = base_tasks + (1 if i < remainder else 0)
        current_end = current_start + tasks_for_this_worker
        
        ranges.append((current_start, current_end))
        current_start = current_end
    
    return ranges


def run_task(worker_id: int, command_parts: List[str], params: Dict[str, str], 
             start_idx: int, end_idx: int, lock: threading.Lock, delay: int = 0) -> Tuple[int, int, str]:
    """
    在子进程中运行单个任务
    
    参数:
        worker_id: 工作线程ID
        command_parts: 命令部分
        params: 参数字典
        start_idx: 起始索引
        end_idx: 结束索引
        lock: 用于同步打印的锁
        delay: 启动延迟（秒）
    
    返回:
        (worker_id, return_code, output): 工作线程ID、返回码和输出
    """
    # 如果有延迟，先等待
    if delay > 0:
        with lock:
            print(f"⏱️  Worker {worker_id}: 等待 {delay} 秒后启动...")
        time.sleep(delay)
    
    # 构建命令
    cmd = command_parts.copy()
    
    # 添加参数，替换 start 和 end index
    for param, value in params.items():
        cmd.append(param)
        if param == '--task_start_index':
            cmd.append(str(start_idx))
        elif param == '--task_end_index':
            cmd.append(str(end_idx))
        else:
            cmd.append(value)
    
    # 继承父进程的环境变量
    env = os.environ.copy()
    
    with lock:
        print(f"\n{'='*80}")
        print(f"🚀 Worker {worker_id}: 启动任务 ({start_idx}, {end_idx}]")
        print(f"   命令: {' '.join(cmd)}")
        print(f"{'='*80}\n")
    
    try:
        # 运行子进程
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        # 实时输出，并添加 worker 标识
        for line in process.stdout:
            prefixed_line = f"[Worker {worker_id}] {line.rstrip()}"
            with lock:
                print(prefixed_line)
            output_lines.append(line)
        
        process.wait()
        return_code = process.returncode
        
        with lock:
            if return_code == 0:
                print(f"\n✓ Worker {worker_id}: 任务完成 ({start_idx}, {end_idx}] - 成功")
            else:
                print(f"\n✗ Worker {worker_id}: 任务完成 ({start_idx}, {end_idx}] - 失败 (退出码: {return_code})")
        
        return worker_id, return_code, ''.join(output_lines)
        
    except Exception as e:
        with lock:
            print(f"\n✗ Worker {worker_id}: 执行出错 - {str(e)}")
        return worker_id, -1, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='并行执行脚本任务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用 4 个并行工作线程
    python parallel_run.py scripts/code/cc_bfs.sh --num_workers 4
    
    # 使用 8 个工作线程，并覆盖索引范围
    python parallel_run.py scripts/code/cc_bfs.sh --num_workers 8 --override_start 0 --override_end 400
        """
    )
    
    parser.add_argument('script_path', help='要执行的 shell 脚本路径')
    parser.add_argument('--num_workers', type=int, default=4, help='并行工作线程数 (默认: 4)')
    parser.add_argument('--override_start', type=int, help='覆盖脚本中的起始索引')
    parser.add_argument('--override_end', type=int, help='覆盖脚本中的结束索引')
    parser.add_argument('--start_delay', type=int, default=5, help='每个 worker 的启动间隔（秒），默认: 5')
    
    args = parser.parse_args()
    
    # 检查脚本是否存在
    if not os.path.exists(args.script_path):
        print(f"错误: 脚本文件不存在: {args.script_path}")
        sys.exit(1)
    
    # 解析脚本
    print(f"📝 解析脚本: {args.script_path}")
    command_parts, params = parse_shell_script(args.script_path)
    
    # 获取任务范围
    start_idx = args.override_start if args.override_start is not None else int(params.get('--task_start_index', 0))
    end_idx = args.override_end if args.override_end is not None else int(params.get('--task_end_index', 100))
    
    print(f"📊 任务范围: ({start_idx}, {end_idx}]")
    print(f"👥 并行数: {args.num_workers}")
    print(f"⏱️  启动间隔: {args.start_delay} 秒")
    
    # 拆分任务范围
    ranges = split_range(start_idx, end_idx, args.num_workers)
    
    print(f"\n📋 任务分配:")
    for i, (s, e) in enumerate(ranges):
        delay = i * args.start_delay
        print(f"   Worker {i}: ({s}, {e}] - {e - s} 个任务 (延迟 {delay}s)")
    
    # 创建线程锁用于同步输出
    lock = threading.Lock()
    
    # 使用线程池并行执行
    print(f"\n{'='*80}")
    print("🏃 开始并行执行...")
    print(f"{'='*80}\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = []
        for worker_id, (s, e) in enumerate(ranges):
            delay = worker_id * args.start_delay
            future = executor.submit(run_task, worker_id, command_parts, params, s, e, lock, delay)
            futures.append(future)
        
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"任务执行异常: {e}")
    
    # 汇总结果
    print(f"\n{'='*80}")
    print("📊 执行结果汇总:")
    print(f"{'='*80}")
    
    success_count = 0
    failed_count = 0
    
    for worker_id, return_code, _ in sorted(results, key=lambda x: x[0]):
        status = "✓ 成功" if return_code == 0 else f"✗ 失败 (退出码: {return_code})"
        print(f"   Worker {worker_id}: {status}")
        if return_code == 0:
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n总计: {success_count} 成功, {failed_count} 失败")
    
    # 如果有失败的任务，返回非零退出码
    if failed_count > 0:
        sys.exit(1)
    else:
        print("\n✓ 所有任务执行成功!")
        sys.exit(0)


if __name__ == '__main__':
    main()
