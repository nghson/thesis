#include "ff_heuristic.h"
#include <stdio.h>

using std::vector;

#define STATUS_DONE 0
#define STATUS_FIXPOINT 1

bool is_fixpoint(const uint64_t* ff_state, const uint64_t* prev_state) {
    static bool first_call = true;
    if (first_call) {
        first_call = false;
        return false;
    }

    for (int i = 0; i < FF_STATE_LENGTH; i++) {
        if (ff_state[i] != prev_state[i]) {
            return false;
        }
    }
    return true;
}

void copy_state(const uint64_t* src, uint64_t* dst) {
    for (int i = 0; i < FF_STATE_LENGTH; i++) {
        dst[i] = src[i];
    }
}

void check_preconds_layer(vector<int>& fact_membership, vector<int>& action_membership) {
    for (int action_idx = 0; action_idx < action_membership.size(); action_idx++) {
        if (action_membership[action_idx] == -1) {
            continue;
        }
        auto preconds = get_preconds_for_action(action_idx);
        for (int precond : preconds) {
            assert(fact_membership[precond] <= action_membership[action_idx]);
        }
    }
}

void check_achieving_action_layer(vector<int>& fact_membership, vector<int>& action_membership, vector<int>& achieving_action) {
    for (int fact_idx = 0; fact_idx < fact_membership.size(); fact_idx++) {
        int achieving_action_idx = achieving_action[fact_idx];
        int action_layer = action_membership[achieving_action_idx];
        int fact_layer = fact_membership[fact_idx];
        assert(action_layer < fact_layer);
    }
}

int build_relaxed_graph(uint64_t* ff_state, vector<int>& fact_membership, vector<int>& action_membership, vector<int>& achieving_action, vector<vector<int>>& G) {
    uint64_t prev_state[FF_STATE_LENGTH] = {0};
    int layer = 0;
    while (true) {
        if (is_ff_goal(ff_state)) {
            return STATUS_DONE;
        }
        if (is_fixpoint(ff_state, prev_state)) {
            return STATUS_FIXPOINT;
        }
        copy_state(ff_state, prev_state);
        build_next_layer(ff_state, prev_state, fact_membership, action_membership, achieving_action, layer, G);
        layer++;
    }
}

void ff_heuristic(uint64_t* state) {
    vector<int> fact_membership(FACT_NUM, -1);
    vector<int> action_membership(ACTION_NUM, -1);
    vector<int> achieving_action(FACT_NUM, -1);
    vector<vector<int>> G;
    vector<bool> marked_fact(FACT_NUM, false);
    
    uint64_t ff_state[FF_STATE_LENGTH] = {0};
    convert_state_to_multi_valued(state, ff_state, fact_membership);

    int status_code = build_relaxed_graph(ff_state, fact_membership, action_membership, achieving_action, G);
    // check_preconds_layer(fact_membership, action_membership);
    // check_achieving_action_layer(fact_membership, action_membership, achieving_action);

    if (status_code == STATUS_FIXPOINT) {
        // set heuristic to be the largest value
        // printf("FIX POINT\n");
        state[STATE_LENGTH] = UINT64_MAX;
        return;
    }

    uint64_t h = 0;
    vector<int> sol;
    for (int l = G.size() - 1; l >= 0; l--) {
        for (int goal_fact_index : G[l]) {
            assert(fact_membership[goal_fact_index] == l + 1);
            if (marked_fact[goal_fact_index]) {
                continue;
            }
            int achieving_action_index = achieving_action[goal_fact_index];
            assert(action_membership[achieving_action_index] < l + 1);
            sol.push_back(achieving_action_index);
            vector<int> preconds = get_preconds_for_action(achieving_action_index);
            for (int precond_idx : preconds) {
                int fact_layer = fact_membership[precond_idx];
                if (fact_layer > action_membership[achieving_action_index]) {
                    printf("goal: %d-%d, action: %d-%d, precond: %d-%d\n", goal_fact_index, fact_membership[goal_fact_index], achieving_action_index, action_membership[achieving_action_index], precond_idx, fact_membership[precond_idx]);
                }
                assert(fact_layer <= action_membership[achieving_action_index]);
                assert(fact_layer < l + 1);
                if (fact_layer == 0) {
                    continue;
                }
                // there is a difference between graph layer and G layer, where G layer index 0 actually means layer 1
                G[fact_layer - 1].push_back(precond_idx);
            }

            vector<int> effects = get_effects_for_action(achieving_action_index);
            for (int effect_idx : effects) {
                if (fact_membership[effect_idx] == l + 1) {
                    marked_fact[effect_idx] = true;
                }
            }
        }
    }

    h = sol.size();

    state[STATE_LENGTH] = h;
}
