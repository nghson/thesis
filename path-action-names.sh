N_BENCHMARK_LINES=4
./planner gbfs > planner-output
if grep -q Success planner-output; then
    mapfile -t action_id < <(tail -n +$((N_BENCHMARK_LINES+2))  planner-output)
    mapfile -t action_names < <(grep -A 1 'begin_operator' $1 | grep -v 'begin_operator' | grep -v '\-\-')
    rm -rf planner_plan
    for id in "${action_id[@]}"; do
        echo "(${action_names[id]})" >> planner_plan
    done
    cat planner_plan
    head -n $((N_BENCHMARK_LINES+1)) planner-output | tail -n +2
    rm -rf planner-output
else
    echo "No plan found."
fi
