#!/usr/bin/env python3
import logging
import sys

from generate import constants, helpers


class FactPair:
    var: int
    value: int

    def __init__(self, var: int, value: int):
        self.var = var
        self.value = value

    # TODO: see if needed to add the remaining methods of FactPair and no_fact


class ExplicitVariable:
    domain_size: int
    name: str
    fact_names: list[str]
    axiom_layer: int
    axiom_default_value: int

    def __init__(self, lines):
        helpers.check_magic(next(lines), "begin_variable")
        self.name = next(lines)
        self.axiom_layer = int(next(lines))
        self.domain_size = int(next(lines))
        self.fact_names = []
        for _ in range(self.domain_size):
            self.fact_names.append(next(lines))
        helpers.check_magic(next(lines), "end_variable")
        self.axiom_default_value = -1


class ExplicitEffect:
    fact: FactPair
    conditions: list[FactPair]

    def __init__(self, var: int, value: int, conditions: list[FactPair]):
        self.fact = FactPair(var, value)
        self.conditions = conditions


def read_facts(lines) -> list[FactPair]:
    count = int(next(lines))
    facts = []
    for i in range(count):
        line = next(lines)
        line = line.split()
        facts.append(FactPair(int(line[0]), int(line[1])))
    return facts


class ExplicitOperator:
    preconditions: list[FactPair]
    effects: list[ExplicitEffect]
    effect_preconditions: list[FactPair]
    cost: int
    name: str
    is_an_axiom: bool

    def __init__(self, lines, is_an_axiom: bool, use_metric: bool):
        self.is_an_axiom = is_an_axiom
        self.effects = []
        self.preconditions = []
        self.effect_preconditions = []
        if not self.is_an_axiom:
            helpers.check_magic(next(lines), "begin_operator")
            self.name = next(lines)
            self.preconditions = read_facts(lines)
            count = int(next(lines))
            for _ in range(count):
                self.read_pre_post(lines)
            op_cost = int(next(lines))
            self.cost = op_cost if use_metric else 1
            helpers.check_magic(next(lines), "end_operator")
        else:
            self.name = "<axiom>"
            self.cost = 0
            helpers.check_magic(next(lines), "begin_rule")
            self.read_pre_post(lines)
            helpers.check_magic(next(lines), "end_rule")
        assert self.cost >= 0

    def read_pre_post(self, lines):
        if not self.is_an_axiom:
            line = next(lines)
            line = line.split()
            index = 0
            conditions: list[FactPair] = []
            count = int(line[index])
            for _ in range(count):
                conditions.append(FactPair(int(line[index + 1]), int(line[index + 2])))
                index += 2
            index += 1
            var = int(line[index])
            value_pre = int(line[index + 1])
            value_post = int(line[index + 2])
            self.effect_preconditions.append(FactPair(var, value_pre))
            if value_pre != -1:
                self.preconditions.append(FactPair(var, value_pre))
            self.effects.append(ExplicitEffect(var, value_post, conditions))
        else:
            conditions: list[FactPair] = read_facts(lines)
            line = next(lines)
            line = line.split()
            var = int(line[0])
            value_pre = int(line[1])
            value_post = int(line[2])
            if value_pre != -1:
                self.preconditions.append(FactPair(var, value_pre))
            self.effects.append(ExplicitEffect(var, value_post, conditions))


def read_and_verify_version(lines):
    helpers.check_magic(next(lines), "begin_version")
    version = int(next(lines))
    helpers.check_magic(next(lines), "end_version")
    if version != constants.PRE_FILE_VERSION:
        logging.error(
            f"Expected translator output file version {constants.PRE_FILE_VERSION} got {version}."
        )
        sys.exit("Search input error")


def read_metric(lines) -> bool:
    helpers.check_magic(next(lines), "begin_metric")
    use_metric = next(lines) == "1"
    helpers.check_magic(next(lines), "end_metric")
    return use_metric


def read_variables(lines) -> list[ExplicitVariable]:
    count = int(next(lines))
    variables = []
    for _ in range(count):
        variables.append(ExplicitVariable(lines))
    return variables


def read_mutexes_raw(lines, n_groups) -> list[list[FactPair]]:
    mutexes_raw = []
    for _ in range(n_groups):
        helpers.check_magic(next(lines), "begin_mutex_group")
        num_facts = int(next(lines))
        invariant_group: list[FactPair] = []
        for _ in range(num_facts):
            line = next(lines)
            line = line.split()
            invariant_group.append(FactPair(int(line[0]), int(line[1])))
        helpers.check_magic(next(lines), "end_mutex_group")
        mutexes_raw.append(invariant_group)
    return mutexes_raw


def read_mutexes(lines, variables: list[ExplicitVariable]) -> tuple[list[list[set[FactPair]]], list[list[FactPair]]]:
    mutexes = []
    for i in range(len(variables)):
        inner: list[set[FactPair]] = [set()] * variables[i].domain_size
        mutexes.append(inner)
    num_mutex_groups = int(next(lines))
    mutexes_raw = read_mutexes_raw(lines, num_mutex_groups)
    for invariant_group in mutexes_raw:
        for fact1 in invariant_group:
            for fact2 in invariant_group:
                if fact1.var != fact2.var:
                    mutexes[fact1.var][fact1.value].add(fact2)
    return (mutexes, mutexes_raw)


def read_goal(lines) -> list[FactPair]:
    helpers.check_magic(next(lines), "begin_goal")
    goals = read_facts(lines)
    helpers.check_magic(next(lines), "end_goal")
    if not goals:
        logging.error("No goal")
        sys.exit("Search input error")
    return goals


def check_fact(fact: FactPair, variables: list[ExplicitVariable]):
    if not helpers.in_bounds(fact.var, variables):
        logging.error(f"Invalid variable id: {fact.var}")
        sys.exit("Search input error")

    if (fact.value < 0) or (fact.value >= variables[fact.var].domain_size):
        logging.error(f"Invalid value of variable: {fact.var}: {fact.value}")
        sys.exit("Search input error")


def check_facts(facts: list[FactPair], variables: list[ExplicitVariable]):
    for fact in facts:
        check_fact(fact, variables)


def check_op(op: ExplicitOperator, variables: list[ExplicitVariable]):
    check_facts(op.preconditions, variables)
    for effect in op.effects:
        check_fact(effect.fact, variables)
        check_facts(effect.conditions, variables)


def read_action(
    lines, is_axiom: bool, use_metric: bool, variables: list[ExplicitVariable]
) -> list[ExplicitOperator]:
    count = int(next(lines))
    actions: list[ExplicitOperator] = []
    for _ in range(count):
        actions.append(ExplicitOperator(lines, is_axiom, use_metric))
        check_op(actions[-1], variables)
    return actions


class RootTask:
    variables: list[ExplicitVariable]
    mutexes: list[list[set[FactPair]]]
    mutexes_raw: list[list[FactPair]]
    operators: list[ExplicitOperator]
    axioms: list[ExplicitOperator]
    initial_state_values: list[int]
    goals: list[FactPair]
    use_metrics: bool

    def __init__(self, lines):
        read_and_verify_version(lines)
        self.use_metrics = read_metric(lines)
        self.variables = read_variables(lines)
        self.mutexes, self.mutexes_raw = read_mutexes(lines, self.variables)
        num_variables = len(self.variables)
        self.initial_state_values = []
        helpers.check_magic(next(lines), "begin_state")
        for i in range(num_variables):
            self.initial_state_values.append(int(next(lines)))
        helpers.check_magic(next(lines), "end_state")
        for i in range(num_variables):
            self.variables[i].axiom_default_value = self.initial_state_values[i]
        self.goals = read_goal(lines)
        check_facts(self.goals, self.variables)
        self.operators = read_action(lines, False, self.use_metrics, self.variables)
        self.axioms = read_action(lines, True, self.use_metrics, self.variables)

        # TODO: axiom eval

    def _get_variable(self, var: int) -> ExplicitVariable:
        assert helpers.in_bounds(var, self.variables)
        return self.variables[var]

    def _get_effect(self, op_id: int, effect_id: int, is_axiom: bool) -> ExplicitEffect:
        op: ExplicitOperator = self._get_operator_or_axiom(op_id, is_axiom)
        assert helpers.in_bounds(effect_id, op.effects)
        return op.effects[effect_id]

    def _get_operator_or_axiom(self, index: int, is_axiom: bool) -> ExplicitOperator:
        if is_axiom:
            assert helpers.in_bounds(index, self.axioms)
            return self.axioms[index]
        else:
            assert helpers.in_bounds(index, self.operators)
            return self.operators[index]

    def get_num_variables(self) -> int:
        return len(self.variables)

    def get_variable_name(self, var: int) -> str:
        return self._get_variable(var).name

    def get_variable_domain_size(self, var: int) -> int:
        return self._get_variable(var).domain_size

    def get_variable_axiom_layer(self, var: int) -> int:
        return self._get_variable(var).axiom_layer

    def get_variable_default_axiom_value(self, var: int) -> int:
        return self._get_variable(var).axiom_default_value

    def get_fact_name(self, fact: FactPair) -> str:
        assert helpers.in_bounds(fact.value, self._get_variable(fact.var).fact_names)
        return self._get_variable(fact.var).fact_names[fact.value]

    def are_facts_mutex(self, fact1: FactPair, fact2: FactPair) -> bool:
        if fact1.var == fact2.var:
            # Same variable: mutex iff different value.
            return fact1.value != fact2.value
        assert helpers.in_bounds(fact1.var, self.mutexes)
        assert helpers.in_bounds(fact1.value, self.mutexes[fact1.var])
        return fact2 in self.mutexes[fact1.var][fact1.value]

    def get_operator_cost(self, index: int, is_axiom: bool) -> int:
        return self._get_operator_or_axiom(index, is_axiom).cost

    def get_operator_name(self, index: int, is_axiom: bool) -> str:
        return self._get_operator_or_axiom(index, is_axiom).name

    def get_num_operators(self) -> int:
        return len(self.operators)

    def get_num_operator_preconditions(self, index: int, is_axiom: bool) -> int:
        return len(self._get_operator_or_axiom(index, is_axiom).preconditions)

    def get_operator_precondition(
        self, op_index: int, fact_index: int, is_axiom: bool
    ) -> FactPair:
        op: ExplicitOperator = self._get_operator_or_axiom(op_index, is_axiom)
        assert helpers.in_bounds(fact_index, op.preconditions)
        return op.preconditions[fact_index]

    def get_num_operator_effects(self, op_index: int, is_axiom: bool) -> int:
        return len(self._get_operator_or_axiom(op_index, is_axiom).effects)

    def get_num_operator_effect_conditions(
        self, op_index: int, eff_index: int, is_axiom: bool
    ) -> int:
        return len(self._get_effect(op_index, eff_index, is_axiom).conditions)

    def get_operator_effect_condition(
        self, op_index: int, eff_index: int, cond_index: int, is_axiom: bool
    ) -> FactPair:
        effect: ExplicitEffect = self._get_effect(op_index, eff_index, is_axiom)
        assert helpers.in_bounds(cond_index, effect.conditions)
        return effect.conditions[cond_index]

    def get_operator_effect(
        self, op_index: int, eff_index: int, is_axiom: bool
    ) -> FactPair:
        return self._get_effect(op_index, eff_index, is_axiom).fact

    def get_num_axioms(self) -> int:
        return len(self.axioms)

    def get_num_goals(self) -> int:
        return len(self.goals)

    def get_goal_fact(self, index: int) -> FactPair:
        assert helpers.in_bounds(index, self.goals)
        return self.goals[index]

    def get_initial_state_values(self) -> list[int]:
        return self.initial_state_values
