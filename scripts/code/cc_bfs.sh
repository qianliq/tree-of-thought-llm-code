python run.py \
    --task code \
    --code_dataset code_contests.jsonl \
    --backend qwen3-coder-plus \
    --task_start_index 0 \
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