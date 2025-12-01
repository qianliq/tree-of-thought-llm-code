import os
import json
import argparse
from tqdm import tqdm

import dotenv
dotenv.load_dotenv()

from tot.tasks import get_task
from tot.methods.bfs import solve, naive_solve
from tot.models import gpt_usage

def run(args):
    task = get_task(args.task)
    logs, cnt_avg, cnt_any = [], 0, 0
    # file path setup
    if args.task == 'code':
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        file = f'./logs/{args.task}/{args.backend}_{args.code_dataset}_{ts}.jsonl'
    else:
        if args.naive_run:
            file = f'./logs/{args.task}/{args.backend}_{args.temperature}_naive_{args.prompt_sample}_sample_{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
        else:
            file = f'./logs/{args.task}/{args.backend}_{args.temperature}_{args.method_generate}{args.n_generate_sample}_{args.method_evaluate}{args.n_evaluate_sample}_{args.method_select}{args.n_select_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
    os.makedirs(os.path.dirname(file), exist_ok=True)

    for i in tqdm(range(args.task_start_index, args.task_end_index), desc=f"{args.task} {args.backend}"):
        # solve
        if args.naive_run:
            ys, info = naive_solve(args, task, i) 
        else:
            ys, info = solve(args, task, i)

        # log
        infos = [task.test_output(i, y) for y in ys]
        # info.update({'idx': i, 'ys': ys, 'infos': infos, 'usage_so_far': gpt_usage(args.backend)})
        if args.task == 'code':
            with open(file, 'a') as f:
                for rec in infos:
                    json.dump({'task_id': rec.get('task_id'), 'code': rec.get('code')}, f, ensure_ascii=False)
                    f.write('\n')
        else:
            logs.append(info)
            with open(file, 'w') as f:
                json.dump(logs, f, indent=4)
    
    if args.task != 'code':
        n = args.task_end_index - args.task_start_index
        print(cnt_avg / n, cnt_any / n)
        print('usage_so_far', gpt_usage(args.backend))


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--backend', type=str, choices=['gpt-4.1-nano', 'qwen3-coder-plus', 'gpt-4o-mini'], default='gpt-4.1-nano')
    args.add_argument('--temperature', type=float, default=0.7)

    args.add_argument('--task', type=str, required=True, choices=['game24', 'text', 'crosswords', 'code'])
    # For code task
    args.add_argument('--code_dataset', type=str, choices=['mbppplus.jsonl', 'humanevalplus.jsonl', 'code_contests.jsonl'], default='mbppplus.jsonl')
    args.add_argument('--task_start_index', type=int, default=900)
    args.add_argument('--task_end_index', type=int, default=1000)

    args.add_argument('--naive_run', action='store_true')
    args.add_argument('--prompt_sample', type=str, choices=['standard', 'cot'])  # only used when method_generate = sample, or naive_run

    args.add_argument('--method_generate', type=str, choices=['sample', 'propose'])
    args.add_argument('--method_evaluate', type=str, choices=['value', 'vote'])
    args.add_argument('--method_select', type=str, choices=['sample', 'greedy'], default='greedy')
    args.add_argument('--n_generate_sample', type=int, default=1)  # only thing needed if naive_run
    args.add_argument('--n_evaluate_sample', type=int, default=1)
    args.add_argument('--n_select_sample', type=int, default=1)

    args = args.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    print(args)
    if args.task == 'code':
        os.environ['CODE_DATASET'] = args.code_dataset
    run(args)