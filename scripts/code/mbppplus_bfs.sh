python run.py \
    --task code \
    --code_dataset mbppplus.jsonl \
    --backend gpt-4o-mini \
    --task_start_index 377 \
    --task_end_index 378 \
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