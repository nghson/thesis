#!/usr/bin/env python3
from dataclasses import dataclass, field

import numpy as np

from generate import parse


@dataclass
class VarInfo:
    """
    b_start is the index of the bit 
    """
    b_start: int
    b_end: int
    b_length: int
    word_pos: int
    mask_get: np.uint64
    mask_set: np.uint64


def get_var_infos(root_task: parse.RootTask) -> list[VarInfo]:
    """
    Gets the information about the variables in the bit state.
    """
    var_infos: list[VarInfo] = []
    index = 0
    word_pos = 0

    for i in range(root_task.get_num_variables()):
        n = 1
        while (1 << n) < root_task.get_variable_domain_size(i):
            n += 1
        if index + n > 64:
            index = 0
            word_pos += 1
        # mask to get the values of the variable's bits
        mask_get: np.uint64 = np.uint64(((1 << n) - 1) << index)
        # mask to clear the values of the variable's bits
        mask_set: np.uint64 = ~mask_get
        var_info = VarInfo(
            b_start=index,
            b_end=index + n - 1,
            b_length=n,
            word_pos=word_pos,
            mask_get=mask_get,
            mask_set=mask_set
        )
        var_infos.append(var_info)
        index += n

    return var_infos


@dataclass
class OperatorPair:
    mask: np.uint64
    val: np.uint64


@dataclass
class OperatorRepr:
    preconds: dict[int, OperatorPair] = field(default_factory=dict)
    effects: dict[int, OperatorPair] = field(default_factory=dict)


def get_op_rep(root_task: parse.RootTask, var_infos: list[VarInfo], op_index: int) -> OperatorRepr:
    op_rep = OperatorRepr()
    preconds = [root_task.get_operator_precondition(op_index, precond_ind, False) for precond_ind in range(
        root_task.get_num_operator_preconditions(op_index, False))]

    for precond in preconds:
        precond_mask = np.uint64(0)
        precond_val = np.uint64(0)
        var_info = var_infos[precond.var]
        state_ind = var_info.word_pos

        # if mask and val are defined then modify them rather than make new
        if state_ind in op_rep.preconds:
            precond_mask = op_rep.preconds[state_ind].mask
            precond_val = op_rep.preconds[state_ind].val

        # we make the assumption that the same bit region in a word is only modified once i.e.
        # a variable fact only appears once in the precond and in the effect. Therefore, those
        # bits are 0 until as init and only modified here

        # set the bits of the variable we need to read
        precond_mask = precond_mask | (((1 << var_info.b_length) - 1) << (var_info.b_start))

        # create the value using the right number of bits, then shift left if needed to match the variable position
        precond_val = precond_val | ((((1 << var_info.b_length) - 1) & precond.value) << (var_info.b_start))

        # update precond with new values
        op_rep.preconds[state_ind] = OperatorPair(precond_mask, precond_val)

    # similar fashion to preconditions
    effects = [root_task.get_operator_effect(op_index, eff_index, False)
               for eff_index in range(root_task.get_num_operator_effects(op_index, False))]
    for effect in effects:
        eff_mask = ~(np.uint64(0))
        eff_val = np.uint64(0)
        var_info = var_infos[effect.var]
        state_ind = var_info.word_pos

        if state_ind in op_rep.effects:
            eff_mask = op_rep.effects[state_ind].mask
            eff_val = op_rep.effects[state_ind].val

        eff_mask = eff_mask & (~np.uint64(((1 << var_info.b_length) - 1) << (var_info.b_start)))
        eff_val = eff_val | ((((1 << var_info.b_length) - 1) & effect.value) << (var_info.b_start))

        op_rep.effects[state_ind] = OperatorPair(eff_mask, eff_val)
    return op_rep


def get_all_op_reps(root_task: parse.RootTask, var_infos: list[VarInfo]) -> list[OperatorRepr]:
    all_op_reps = []
    for op_index in range(root_task.get_num_operators()):
        op_reps = get_op_rep(root_task, var_infos, op_index)
        all_op_reps.append(op_reps)
    return all_op_reps
