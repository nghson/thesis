#!/usr/bin/env python3
import os
from typing import Optional

import numpy as np

from generate import constants, parse, representations, helpers


ACTION_FILE = "action.cpp"
ACTION_HEADER = "action.h"
CONFIG_FILE = "config.h"

SA_ACTION_FILE = "sa_action.cpp"
SA_ACTION_HEADER = "sa_action.h"


def write_configs(var_infos: list[representations.VarInfo]):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, CONFIG_FILE)
    with open(filepath, "w") as file:
        file.write("#ifndef CONFIG_H\n#define CONFIG_H\n")
        state_length = var_infos[-1].word_pos + 1
        # file.write(f"#define STATE_LENGTH {state_length}\n")
        # file.write("#define STATE_LENGTH_HEU STATE_LENGTH + 1\n")
        # file.write(f"#define STORAGE_LENGTH {constants.STORAGE_LENGTH}\n")
        file.write(f"const int STATE_LENGTH = {state_length};\n")
        file.write("const int STATE_LENGTH_HEU = STATE_LENGTH + 1;\n")
        file.write(f"const int STORAGE_LENGTH = {constants.STORAGE_LENGTH};\n")
        file.write("#endif")


def write_actions(root_task: parse.RootTask, var_infos: list[representations.VarInfo]):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, ACTION_FILE)
    op_reps = representations.get_all_op_reps(root_task, var_infos)
    initial_state_str = make_initial_state_str(root_task, var_infos)
    goal_str = make_goal_str(root_task, var_infos)
    state_length = var_infos[-1].word_pos + 1
    with open(filepath, "w") as file:
        file.write(f'#include "{ACTION_HEADER}"\n\n')
        file.write(("void actions(uint64_t* state_bitrep, PlannerQueue& pq, PathInfoMap& path_info) {\n"))
        for action_idx, op_rep in enumerate(op_reps):
            precond_str = make_precond_str(op_rep.preconds)
            mutex_str = make_mutex_str_for_action(root_task, var_infos, action_idx)
            effect_str = make_effect_str(action_idx, op_rep.effects, state_length, mutex_str)
            if precond_str:
                file.write(f"if ({precond_str})\n")
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


def make_effect_str(action_idx: int, effects: dict[int, representations.OperatorPair], state_length: int, mutex_str: Optional[str]) -> str:
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
    effect_str = "\n".join(effect_str_list)
    newstate_bitrep_str = "uint64_t* newstate_bitrep = allocate_state();\n"
    add_newstate_to_queue = f"{{add_to_queue(newstate_bitrep, state_bitrep, {action_idx}, pq, path_info);}}\n"
    if mutex_str:
        mutex_test_str = f"if ({mutex_str})\n"
        mutex_fail_str = "else {remove_last();}\n"
        add_newstate_to_queue = mutex_test_str + add_newstate_to_queue + mutex_fail_str
    res = newstate_bitrep_str + effect_str + "\n" + add_newstate_to_queue
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


def make_mutex_str_for_action(
    root_task: parse.RootTask, var_infos: list[representations.VarInfo], action_idx: int
) -> Optional[str]:
    res = []
    mutexes = root_task.get_operator_mutexes(action_idx)
    # print(f"mutex for action {action_idx}")
    for fact in mutexes:
        # print(fact.var, fact.value)
        var_info = var_infos[fact.var]
        val = np.uint64(0) | (fact.value << var_info.b_start)
        res.append(f"((newstate_bitrep[{var_info.word_pos}] & {bin(var_info.mask_get)}) != {bin(val)})")
    return ' && '.join(res) if len(res) > 0 else None


def write_sa_actions(root_task: parse.RootTask, var_infos: list[representations.VarInfo]):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, SA_ACTION_FILE)
    get_applicable_actions_str = make_get_applicable_actions_str(root_task, var_infos)
    apply_action_effects_str = make_apply_action_effects_str(root_task, var_infos)
    with open(filepath, "w") as file:
        file.write("#include \"sa_action.h\"\n")
        file.write(get_applicable_actions_str)
        file.write(apply_action_effects_str)


def make_get_applicable_actions_str(root_task: parse.RootTask, var_infos: list[representations.VarInfo]) -> str:
    op_reps = representations.get_all_op_reps(root_task, var_infos)
    f_str = helpers.FunctionStr(
        "vector<int>",
        "get_applicable_actions",
        ["uint64_t* state_bitrep"]
    )
    f_str.add_body("vector<int> applicable_actions;")
    for action_idx, op_rep in enumerate(op_reps):
        precond_str = make_precond_str(op_rep.preconds)
        if precond_str:
            f_str.add_body(f"if ({precond_str})")
        f_str.add_body("{ " + f"applicable_actions.push_back({action_idx});" + " }")
    f_str.add_body("return applicable_actions;")
    return f_str.make_str()


def make_apply_action_effects_str(root_task: parse.RootTask, var_infos: list[representations.VarInfo]) -> str:
    op_reps = representations.get_all_op_reps(root_task, var_infos)
    state_length = var_infos[-1].word_pos + 1
    f_str = helpers.FunctionStr(
        "void",
        "apply_action_effects",
        ["uint64_t* state_bitrep", "int action_idx"]
    )
    f_str.add_body("uint64_t* newstate_bitrep = allocate_state();")
    for action_idx, op_rep in enumerate(op_reps):
        effect_str = make_new_state_str(action_idx, op_rep.effects, state_length)
        f_str.add_body(effect_str)
    return f_str.make_str()


def write_sa_header():
    filepath = os.path.join(constants.C_SRC_CODE_DIR, SA_ACTION_HEADER)
    with open(filepath, "w") as file:
        file.write("#ifndef SA_ACTION_H\n")
        file.write("#define SA_ACTION_H\n")
        file.write("#include <stdint.h>\n")
        file.write("#include <vector>\n")
        file.write("#include \"storage.h\"\n")
        file.write("using namespace std;\n")
        file.write("vector<int> get_applicable_actions(uint64_t* state_bitrep);\n")
        file.write("void apply_action_effects(uint64_t* state_bitrep, int action_idx);\n")
        file.write("#endif\n")


def make_new_state_str(action_idx: int, effects: dict[int, representations.OperatorPair], state_length: int) -> str:
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
    effect_str = "\n".join(effect_str_list)
    res =  f"if (action_idx == {action_idx}) " + "{\n" + effect_str + "\nreturn;\n}"
    return res
