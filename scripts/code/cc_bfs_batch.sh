# 第1份
python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 0 \
    --task_end_index 32 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}

# 第2份
python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 32 \
    --task_end_index 65 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}

# 第3份
python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 65 \
    --task_end_index 98 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}

# 第4份
python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 98 \
    --task_end_index 131 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}

# 第5份
python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 131 \
    --task_end_index 165 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}