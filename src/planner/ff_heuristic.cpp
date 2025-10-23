#include "ff_heuristic.h"

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

uint64_t extract_h_value(vector<int>& fact_membership, vector<int>& action_membership, vector<int>& achieving_action, int layer) {
    uint64_t h = 0;
    for (int i = layer; i > 0; i--) {
        backward(fact_membership, action_membership, achieving_action, layer, &h);
    }
    return h;
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
            if (marked_fact[goal_fact_index]) {
                continue;
            }
            int achieving_action_index = achieving_action[goal_fact_index];
            sol.push_back(achieving_action_index);
            vector<int> preconds = get_preconds_for_action(achieving_action_index);
            for (int precond_idx : preconds) {
                int fact_layer = fact_membership[precond_idx];
                if (fact_layer == 0) {
                    continue;
                }
                // there is a difference between graph layer and G layer, where G layer index 0 actually means layer 1
                G[fact_layer - 1].push_back(precond_idx);
            }

            vector<int> effects = get_effects_for_action(achieving_action_index);
            for (int effect_idx : effects) {
                if (fact_membership[effect_idx] == l) {
                    marked_fact[effect_idx] = true;
                }
            }
        }
    }

    h = sol.size();

    state[STATE_LENGTH] = h;
}
