#!/usr/bin/env python3
import os
from typing import Optional

import numpy as np

from generate import constants, parse, representations


def write_configs(var_infos: list[representations.VarInfo], filename: str):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, filename)
    with open(filepath, "w") as file:
        file.write("#ifndef CONFIG_H\n#define CONFIG_H\n")
        state_length = var_infos[-1].word_pos + 1
        file.write(f"#define STATE_LENGTH {state_length}\n")
        file.write("#define STATE_LENGTH_HEU STATE_LENGTH + 1\n")
        file.write(f"#define STORAGE_LENGTH {constants.STORAGE_LENGTH}\n")
        file.write("#endif")


def write_actions(root_task: parse.RootTask, var_infos: list[representations.VarInfo], filename: str):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, filename)
    op_reps = representations.get_all_op_reps(root_task, var_infos)
    initial_state_str = make_initial_state_str(root_task, var_infos)
    goal_str = make_goal_str(root_task, var_infos)
    state_length = var_infos[-1].word_pos + 1
    with open(filepath, "w") as file:
        file.write('#include "action.h"\n\n')
        file.write(
            (
                "void actions(uint64_t* state_bitrep, PlannerQueue& pq, std::unordered_map<uint64_t*, std::pair<uint64_t*, int>>& path_info) {\n"
            )
        )
        for action_idx, op_rep in enumerate(op_reps):
            preconds_str = make_precond_str(op_rep.preconds)
            effect_str = make_effect_str(action_idx, op_rep.effects, state_length)
            if preconds_str:
                file.write(f"if ({preconds_str})\n")
            file.write("{\n" + f"{effect_str}" + "}\n")
        file.write("}\n\n")

        file.write(goal_str)

        file.write(initial_state_str)


def make_precond_str(preconds: dict[int, representations.OperatorPair]) -> Optional[str]:
    preconds_str_list = []
    for state_ind in preconds:
        preconds_str_list.append(
            f"((state_bitrep[{state_ind}] & {bin(preconds[state_ind].mask)}) == {bin(preconds[state_ind].val)})"
        )
    res = " && ".join(preconds_str_list) if len(preconds_str_list) > 0 else None
    return res


def make_effect_str(action_idx: int, effects: dict[int, representations.OperatorPair], state_length: int) -> str:
    effect_str_list = []
    for state_ind in range(state_length):
        if state_ind in effects:
            effect_str_list.append(
                (
                    f"newstate_bitrep[{state_ind}] "
                    f"= (state_bitrep[{state_ind}] & {bin(effects[state_ind].mask)})"
                    f" | {bin(effects[state_ind].val)};"
                )
            )
        else:
            effect_str_list.append(f"newstate_bitrep[{state_ind}] = state_bitrep[{state_ind}];")
    res = "\n".join(effect_str_list)
    newstate_bitrep_str = "uint64_t* newstate_bitrep = allocate_state();\n"
    add_path_info_str = make_add_path_info_str(action_idx)
    add_newstate_to_queue = "add_to_queue(newstate_bitrep, pq);\n"
    res = newstate_bitrep_str + res + "\n" + add_path_info_str + add_newstate_to_queue
    return res


def make_add_path_info_str(action_idx: int) -> str:
    res = f"path_info.insert({{newstate_bitrep, std::make_pair(state_bitrep, {action_idx})}});\n"
    return res


def make_initial_state_str(root_task: parse.RootTask, var_infos: list[representations.VarInfo]) -> str:
    res = "uint64_t INITIAL_STATE[STATE_LENGTH_HEU] = "
    state_length = var_infos[-1].word_pos + 1
    state_values = root_task.get_initial_state_values()
    state_nums = [np.uint64(0) for _ in range(state_length)]
    for var, val in enumerate(state_values):
        var_info = var_infos[var]
        state_nums[var_info.word_pos] |= (((1 << var_info.b_length) - 1) & val) << var_info.b_start
    num_str = ",\n".join([bin(n) for n in state_nums])
    res += "{\n" + num_str + ", 0\n};\n"
    return res


def make_goal_str(root_task: parse.RootTask, var_infos: list[representations.VarInfo]) -> str:
    goals = [root_task.get_goal_fact(i) for i in range(root_task.get_num_goals())]
    goal_nums: dict[int, representations.OperatorPair] = {}
    for goal_fact in goals:
        mask = np.uint64(0)
        val = np.uint64(0)
        var_info = var_infos[goal_fact.var]
        state_ind = var_info.word_pos

        if state_ind in goal_nums:
            mask = goal_nums[state_ind].mask
            val = goal_nums[state_ind].val

        mask = mask | (((1 << var_info.b_length) - 1) << var_info.b_start)
        val = val | ((((1 << var_info.b_length) - 1) & goal_fact.value) << var_info.b_start)
        goal_nums[state_ind] = representations.OperatorPair(mask, val)
    cond_str = make_precond_str(goal_nums)
    assert cond_str is not None
    cond_str = "{ return (" + cond_str + "); }"

    res = f"bool is_goal(uint64_t* state_bitrep) {cond_str}\n\n"
    return res
