#include <stdint.h>
#include <stdio.h>

#include <chrono>
#include <cstdint>
#include <queue>
#include <utility>
#include <unordered_map>
#include <stack>
#include <string>
#include <vector>
#include <random>

#include "storage.h"
#include "visited_set.h"
#include "action.h"
#include "h_pqueue.h"
#include "ff_heuristic.h"
#include "sa_action.h"

void greedy_best_first_search();
void simulated_annealing();

int main(int argc, char* argv[]) {
    if (argc == 1) {
        printf("No search algorithm specified.\n");
        return 0;
    }

    std::vector<std::string> args(argv, argv + argc);
    if (args[1] == "gbfs") {
        greedy_best_first_search();
    }
    if (args[1] == "sa") {
        simulated_annealing();
    }
    return 0;
}

void greedy_best_first_search() {
    storage_init();

    PathInfoMap path_info;

    PlannerQueue pq;
    add_to_queue(INITIAL_STATE, NULL, -1, pq, path_info);

    auto start = std::chrono::steady_clock::now();
    const std::chrono::minutes timeout(20);
    uint64_t state_expanded_count = 0;

    bool done = false;
    uint64_t* goal;
    while (!done && !pq.empty()) {
        uint64_t* state = pq.top();
        pq.pop();
        insert_visited(state);
        if (is_goal(state)) {
            printf("Success.\n");
            goal = state;
            done = true;
            continue;
        }

        //expand node then add to pq
        actions(state, pq, path_info);

        state_expanded_count++;
        auto now = std::chrono::steady_clock::now();
        auto elapsed = now - start;
        if (elapsed >= timeout) {
            printf("timeout\n");
            break;
        }
    }

    if (!done) {
        printf("No solution found.\n");
    }

    auto now = std::chrono::steady_clock::now();
    std::chrono::duration<double> total = now - start;
    printf("number of states created: %ld\n", count);
    printf("time elapsed: %f\n", total.count());
    printf("number of states created per second: %f\n", count / total.count());
    printf("number of states expanded per second: %f\n", state_expanded_count / total.count());

    std::stack<int> path;
    uint64_t* current = goal;
    while (current != INITIAL_STATE) {
        auto path_pair = path_info[current];
        current = path_pair.first;
        path.push(path_pair.second);
    }
    while (!path.empty()) {
        printf("%d\n", path.top());
        path.pop();
    }

    free_storage();
}

typedef struct {
    int current_var_state_idx;
    int next_var_state_idx;
    int current_action_idx;
    int next_action_idx;
} SimAnnState;

void simulated_annealing() {
    storage_init();
    std::vector<uint> actions(STORAGE_LENGTH);
    SimAnnState sa_state;
    sa_state.current_action_idx = -1;
    sa_state.current_var_state_idx = -1;

    double T = 10000;
    double u = 0.995;
    ff_heuristic(INITIAL_STATE);
    uint64_t value = INITIAL_STATE[STATE_LENGTH];
    bool done = false;
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    uint64_t* current_var_state = INITIAL_STATE;

    while (T > 1) {
        // next state
        std::vector<int> applicable_actions = get_applicable_actions(current_var_state);
        int action_num = 0;
        if (applicable_actions.size() > 0) {
            std::uniform_int_distribution<> random_action_picker(0, applicable_actions.size());
            action_num = random_action_picker(rng);
        }
        if (false && sa_state.current_action_idx > 2 && action_num == applicable_actions.size()) {
            std::uniform_int_distribution<> random_n_states(1, sa_state.current_action_idx / 2);
            int n_states_to_drop = random_n_states(rng);
            sa_state.next_action_idx = sa_state.current_action_idx - n_states_to_drop;
            sa_state.next_var_state_idx = sa_state.current_var_state_idx - n_states_to_drop * STATE_LENGTH_HEU;
        } else {
            int action_idx = applicable_actions[action_num];
            printf("action %d\n", action_idx);
            apply_action_effects(current_var_state, action_idx);
            if (sa_state.current_action_idx < 0) {
                sa_state.next_action_idx = 0;
            } else {
                sa_state.next_action_idx = sa_state.current_action_idx + 1;
            }
            if (sa_state.current_var_state_idx < 0) {
                sa_state.next_var_state_idx = 0;
            } else {
                sa_state.next_var_state_idx = sa_state.current_var_state_idx + STATE_LENGTH_HEU;
            }
            if (sa_state.next_action_idx < STORAGE_LENGTH) {
                actions[sa_state.next_action_idx] = action_idx;
            } else {
                printf("Out of memory %d.\n", sa_state.next_action_idx);
                abort();
            }
        }
        uint64_t* next_var_state = get_state(sa_state.next_var_state_idx);

        // check goal
        if (is_goal(next_var_state)) {
            printf("Success.\n");
            done = true;
            break;
        }

        // state value
        ff_heuristic(next_var_state);
        uint64_t next_value = sa_state.current_action_idx + next_var_state[STATE_LENGTH];

        // update state
        uint64_t prob = exp(-(next_value - value) / T);
        std::bernoulli_distribution d(prob);
        if (prob > 1 || d(rng)) {
            sa_state.current_var_state_idx = sa_state.next_var_state_idx;
            sa_state.current_action_idx = sa_state.next_action_idx;
            value = next_value;
            current_var_state = next_var_state;
            // update storage when remove actions/states
        } else {
            if (sa_state.next_action_idx > sa_state.current_action_idx) {
                remove_last();
            }
        }
        printf("current state: %ld\n");
        printf("actions: ");
        for (int i = 0; i <= sa_state.current_action_idx; i++) {
            printf("%d ", actions[i]);
        }
        printf("\n");

        T *= u;
    }

    if (!done) {
        printf("No solution found.\n");
    }

    free_storage();
}