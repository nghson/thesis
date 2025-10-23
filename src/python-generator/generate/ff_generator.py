#!/usr/bin/env python3
import os
from typing import Optional

import numpy as np

from generate import constants, parse, representations, helpers

ACTION_FILE = "ff_graph.cpp"
ACTION_HEADER = "ff_graph.h"
CONFIG_FILE = "ff_config.h"


def get_ff_var_infos(root_task: parse.RootTask) -> list[representations.VarInfo]:
    """
    Gets the information about the variables in the bit state for the FF heuristic.
    If a variable can have n values, then its state would be represented by n bits.
    """
    var_infos: list[representations.VarInfo] = []
    index = 0
    word_pos = 0

    for i in range(root_task.get_num_variables()):
        n = root_task.get_variable_domain_size(i)
        if index + n > 64:
            index = 0
            word_pos += 1
        mask_get: np.uint64 = np.uint64(((1 << n) - 1) << index)
        mask_set: np.uint64 = ~mask_get
        var_info = representations.VarInfo(
            index, index + n - 1, n, word_pos, mask_get, mask_set
        )
        var_infos.append(var_info)
        index += n
    return var_infos


def get_ff_op_rep(
    root_task: parse.RootTask,
    ff_var_infos: list[representations.VarInfo],
    op_index: int,
) -> tuple[dict[int, np.uint64], dict[int, np.uint64]]:
    preconds = [
        root_task.get_operator_precondition(op_index, precond_ind, False)
        for precond_ind in range(
            root_task.get_num_operator_preconditions(op_index, False)
        )
    ]
    precond_dict: dict[int, np.uint64] = {}
    for precond in preconds:
        precond_mask = np.uint64(0)
        var_info = ff_var_infos[precond.var]
        state_ind = var_info.word_pos

        if state_ind in precond_dict:
            precond_mask = precond_dict[state_ind]

        # for ff heuristic, since we use n bits to represent n values in the domain of the variable,
        # we only need to get that one bit from the variable state to check the precond.
        # we only need one unit64 for both the mask and the value
        precond_mask = precond_mask | (1 << (precond.value + var_info.b_start))
        precond_dict[state_ind] = precond_mask

    effects = [
        root_task.get_operator_effect(op_index, eff_index, False)
        for eff_index in range(root_task.get_num_operator_effects(op_index, False))
    ]
    effect_dict: dict[int, np.uint64] = {}
    for effect in effects:
        eff_val = np.uint64(0)
        var_info = ff_var_infos[effect.var]
        state_ind = var_info.word_pos

        if state_ind in effect_dict:
            eff_val = effect_dict[state_ind]

        # similarly to the preconds, we only need to set one bit in the variable state
        eff_val = eff_val | (1 << (effect.value + var_info.b_start))
        effect_dict[state_ind] = eff_val

    return precond_dict, effect_dict


def write_ff_configs(
    root_task: parse.RootTask, ff_var_infos: list[representations.VarInfo]
):
    fact_num = 0
    for i in range(root_task.get_num_variables()):
        fact_num += root_task.get_variable_domain_size(i)

    filepath = os.path.join(constants.C_SRC_CODE_DIR, CONFIG_FILE)
    with open(filepath, "w") as file:
        file.write("#ifndef FF_CONFIG_H\n#define FF_CONFIG_H\n")
        state_length = ff_var_infos[-1].word_pos + 1
        file.write(f"#define FF_STATE_LENGTH {state_length}\n")
        file.write(f"#define FACT_NUM {fact_num}\n")
        file.write(f"#define ACTION_NUM {root_task.get_num_operators()}\n")
        file.write("#endif")


def write_ff_graph(
    root_task: parse.RootTask,
    var_infos: list[representations.VarInfo],
    ff_var_infos: list[representations.VarInfo],
):
    filepath = os.path.join(constants.C_SRC_CODE_DIR, ACTION_FILE)

    cumulative_var_domain = get_cumulative_var_domain(root_task)
    multi_valued_conversion_str = make_multi_valued_conversion_str(
        var_infos, ff_var_infos, cumulative_var_domain
    )
    goal_str = make_goal_str(root_task, ff_var_infos)
    build_next_layer_str = make_build_next_layer_str(
        root_task, ff_var_infos, cumulative_var_domain
    )
    backward_str = make_backward_str()
    get_preconds_for_action_str = make_get_preconds_for_action_str(root_task, cumulative_var_domain)
    get_effects_for_action_str = make_get_effects_for_action_str(root_task, cumulative_var_domain)
    with open(filepath, "w") as file:
        file.write(f'#include "{ACTION_HEADER}"\n')
        file.write(multi_valued_conversion_str)
        file.write(goal_str)
        file.write(build_next_layer_str)
        file.write(backward_str)
        file.write(get_preconds_for_action_str)
        file.write(get_effects_for_action_str)


def make_build_next_layer_str(
    root_task: parse.RootTask,
    ff_var_infos: list[representations.VarInfo],
    cumulative_var_domain: list[int],
) -> str:
    f_str = helpers.FunctionStr(
        "void",
        "build_next_layer",
        [
            "uint64_t* next_state",
            "const uint64_t* state",
            "std::vector<int>& fact_membership",
            "std::vector<int>& action_membership",
            "std::vector<int>& achieving_action",
            "int layer",
            "std::vector<std::vector<int>>& G"
        ],
    )

    f_str.add_body("std::vector<int> gi;")

    for action_index in range(root_task.get_num_operators()):
        action_str = make_build_layer_action_str(
            action_index, root_task, ff_var_infos, cumulative_var_domain
        )
        f_str.add_body(action_str)

    f_str.add_body("G.push_back(gi);")

    return f_str.make_str()


def make_build_layer_action_str(
    action_idx: int,
    root_task: parse.RootTask,
    ff_var_infos: list[representations.VarInfo],
    cumulative_var_domain: list[int],
) -> str:
    precond_rep, effect_rep = get_ff_op_rep(root_task, ff_var_infos, action_idx)

    precond_str = make_precond_str(precond_rep)
    precond_str = " && " + precond_str if precond_str else ""

    effect_str = make_effect_str(effect_rep)

    res = f"if (action_membership[{action_idx}] == -1{precond_str})" + " {\n"
    res += effect_str + "\n"
    res += make_action_membership_str(action_idx)
    res += make_action_effects_membership_str(
        action_idx, root_task, cumulative_var_domain
    )
    res += "}"
    return res


def make_action_membership_str(action_idx: int) -> str:
    res = f"action_membership[{action_idx}] = layer;\n"
    return res


def make_action_effects_membership_str(
    action_idx: int, root_task: parse.RootTask, cumulative_var_domain: list[int]
) -> str:
    goal_facts = make_goal_dicts(root_task)
    res = ""
    for eff_idx in range(root_task.get_num_operator_effects(action_idx, False)):
        eff = root_task.get_operator_effect(action_idx, eff_idx, False)
        membership_idx = cumulative_var_domain[eff.var] + eff.value
        res += f"if (fact_membership[{membership_idx}] == -1)" + "{\n"
        res += f"fact_membership[{membership_idx}] = layer + 1;\n"
        res += f"achieving_action[{membership_idx}] = {action_idx};\n"
        res += make_add_fact_to_gi_str(goal_facts, eff.var, eff.value, membership_idx)
        res += "}\n"
    return res


def make_add_fact_to_gi_str(goal_facts: dict[int, int], var: int, value: int, membership_idx: int) -> str:
    if not (var in goal_facts and goal_facts[var] == value):
        return ""
    res = f"gi.push_back({membership_idx});\n"
    return res


def make_goal_dicts(root_task: parse.RootTask):
    d = {}
    for i in range(root_task.get_num_goals()):
        fact = root_task.get_goal_fact(i)
        d[fact.var] = fact.value
    return d


def make_precond_str(preconds: dict[int, np.uint64]) -> Optional[str]:
    preconds_str_list = []
    for state_ind, mask in preconds.items():
        preconds_str_list.append(f"((state[{state_ind}] & {bin(mask)}) == {bin(mask)})")
    res = " && ".join(preconds_str_list) if len(preconds_str_list) > 0 else None
    return res


def make_effect_str(effects: dict[int, np.uint64]) -> str:
    effect_str_list = []
    for state_ind, mask in effects.items():
        effect_str_list.append(
            f"next_state[{state_ind}] = next_state[{state_ind}] | {bin(mask)};"
        )
    res = "\n".join(effect_str_list)
    return res


def make_goal_str(
    root_task: parse.RootTask, ff_var_infos: list[representations.VarInfo]
) -> str:
    goals = [root_task.get_goal_fact(i) for i in range(root_task.get_num_goals())]
    goal_nums: dict[int, np.uint64] = {}
    for goal_fact in goals:
        var_info = ff_var_infos[goal_fact.var]
        state_ind = var_info.word_pos
        mask = np.uint64(0) if state_ind not in goal_nums else goal_nums[state_ind]
        goal_nums[state_ind] = mask | (1 << (goal_fact.value + var_info.b_start))

    str_list = []
    for state_ind, mask in goal_nums.items():
        str_list.append(f"((ff_state[{state_ind}] & {bin(mask)}) == {bin(mask)})")
    assert len(str_list) > 0
    body_str = "return " + " && ".join(str_list) + ";"

    f_str = helpers.FunctionStr("bool", "is_ff_goal", ["uint64_t* ff_state"])
    f_str.add_body(body_str)

    return f_str.make_str()


def make_multi_valued_conversion_str(
    var_infos: list[representations.VarInfo],
    ff_var_infos: list[representations.VarInfo],
    cumulative_var_domain: list[int],
) -> str:
    assert len(var_infos) == len(ff_var_infos)
    f_str = helpers.FunctionStr(
        "void",
        "convert_state_to_multi_valued",
        ["uint64_t* state", "uint64_t* ff_state", "std::vector<int>& fact_membership"],
    )
    for i in range(len(var_infos)):  # pylint: disable=consider-using-enumerate
        var_info = var_infos[i]
        state_ind = var_info.word_pos
        mask = var_info.mask_get
        shift = var_info.b_start
        ff_var_info = ff_var_infos[i]
        ff_state_ind = ff_var_info.word_pos
        ff_shift = ff_var_info.b_start
        f_str.add_body(
            make_multi_vallued_conversion_str_helper(
                state_ind, mask, shift, ff_state_ind, ff_shift, i, cumulative_var_domain
            )
        )
    return f_str.make_str()


def make_multi_vallued_conversion_str_helper(
    state_ind,
    mask,
    shift,
    ff_state_ind,
    ff_shift,
    var_idx: int,
    cumulative_var_domain: list[int],
) -> str:
    get_val_str = f"uint64_t val = (state[{state_ind}] & {bin(mask)}) >> {shift};"
    set_val_str = f"ff_state[{ff_state_ind}] = ff_state[{ff_state_ind}] | (1 << (val + {ff_shift}));"
    before_idx = cumulative_var_domain[var_idx]
    fact_membership_str = f"fact_membership[{before_idx} + val] = 0;"
    res = "{\n" + "\n".join([get_val_str, set_val_str, fact_membership_str]) + "}"
    return res


def get_cumulative_var_domain(root_task: parse.RootTask) -> list[int]:
    n_vars = root_task.get_num_variables()
    l = [0] * n_vars
    for var_idx in range(1, n_vars):
        l[var_idx] = l[var_idx - 1] + root_task.get_variable_domain_size(var_idx - 1)
    return l


def make_backward_str():
    f_str = helpers.FunctionStr(
        "void",
        "backward",
        [
            "std::vector<int>& fact_membership",
            "std::vector<int>& action_membership",
            "std::vector<int>& achieving_action",
            "int layer",
            "uint64_t* h"
        ]
    )

    return f_str.make_str()


def make_get_preconds_for_action_str(root_task: parse.RootTask, cumulative_var_domain: list[int]):
    f_str = helpers.FunctionStr(
        "std::vector<int>",
        "get_preconds_for_action",
        ["int action_idx"]
    )
    for action_idx in range(root_task.get_num_operators()):
        s = f"if (action_idx == {action_idx})" + "{\n"
        if action_idx == root_task.get_num_operators() - 1:
            s = "{\n"
        s += "std::vector<int> precond_idx = {"
        ff_precond_idx_l = []
        for precond_idx in range(root_task.get_num_operator_preconditions(action_idx, False)):
            precond = root_task.get_operator_precondition(action_idx, precond_idx, False)
            ff_precond_idx = cumulative_var_domain[precond.var] + precond.value
            ff_precond_idx_l.append(str(ff_precond_idx))
        s += ",".join(ff_precond_idx_l) + "};\n"
        s += "return precond_idx;\n"
        s += "}\n"
        f_str.add_body(s)
    return f_str.make_str()


def make_get_effects_for_action_str(root_task: parse.RootTask, cumulative_var_domain: list[int]):
    f_str = helpers.FunctionStr(
        "std::vector<int>",
        "get_effects_for_action",
        ["int action_idx"]
    )
    for action_idx in range(root_task.get_num_operators()):
        s = f"if (action_idx == {action_idx})" + "{\n"
        if action_idx == root_task.get_num_operators() - 1:
            s = "{\n"
        s += "std::vector<int> effect_idx = {"
        ff_effect_idx_l = []
        for effect_idx in range(root_task.get_num_operator_effects(action_idx, False)):
            effect = root_task.get_operator_effect(action_idx, effect_idx, False)
            ff_effect_idx = cumulative_var_domain[effect.var] + effect.value
            ff_effect_idx_l.append(str(ff_effect_idx))
        s += ",".join(ff_effect_idx_l) + "};\n"
        s += "return effect_idx;\n"
        s += "}\n"
        f_str.add_body(s)
    return f_str.make_str()
