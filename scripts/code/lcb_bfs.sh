python run.py \
    --task code \
    --code_dataset lcb.jsonl \
    --backend gpt-4.1-nano \
    --task_start_index 45 \
    --task_end_index 400 \
    --method_generate sample \
    --method_evaluate vote \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 5 \
    --n_select_sample 1 \
    --prompt_sample cot \
    --temperature 0.8 \
    ${@}