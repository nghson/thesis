./planner > planner_output
if grep -q Success planner_output; then
    mapfile -t action_id < <(tail -n +6 planner_output)
    mapfile -t action_names < <(grep -A 1 'begin_operator' $1 | grep -v 'begin_operator' | grep -v '\-\-')
    rm -rf planner_plan
    for id in "${action_id[@]}"; do
        echo "(${action_names[id]})" >> planner_plan
    done
    rm -rf planner_output
    cat planner_plan
fi
