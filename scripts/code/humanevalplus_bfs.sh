python run.py \
    --task code \
    --code_dataset humanevalplus.jsonl \
    --backend qwen3-coder-plus \
    --task_start_index 0 \
    --task_end_index 164 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}


# 0.3 dollars per line ->  30 dollars for 100 lines