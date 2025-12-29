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

void simulated_annealing() {
    storage_init();
    std::vector<uint> actions(STORAGE_LENGTH);
    int current_action_idx = -1;
    int current_var_state_idx = -1 * (STATE_LENGTH_HEU);
    uint64_t* current_var_state = INITIAL_STATE;
    ff_heuristic(INITIAL_STATE);
    uint64_t value = INITIAL_STATE[STATE_LENGTH];
    int storage_size = 0;
    int actions_size = 0;

    double T = 10000;
    double u = 0.995;
    bool done = false;
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    int sa_count = 0;
    auto start = std::chrono::steady_clock::now();

    while (T > 1) {
        bool drop = false;
        int action_num = 0;
        int n_states_to_drop = 0;
        int next_action_idx;
        int next_var_state_idx;

        std::vector<int> applicable_actions = get_applicable_actions(current_var_state);

        if (applicable_actions.size() > 1) {
            // we only consider dropping actions if we have taken at least 1 action
            int max_action_num = current_action_idx >= 0 ? applicable_actions.size() : applicable_actions.size() - 1;
            std::uniform_int_distribution<> random_action_picker(0, max_action_num);
            action_num = random_action_picker(rng);
        }
        if (action_num == applicable_actions.size()) {
            drop = true;
            std::uniform_int_distribution<> random_n_states(1, current_action_idx + 1);
            n_states_to_drop = random_n_states(rng);
            next_action_idx = current_action_idx - n_states_to_drop;
            next_var_state_idx = current_var_state_idx - n_states_to_drop * STATE_LENGTH_HEU;
        } else {
            int action_idx = applicable_actions[action_num];
            apply_action_effects(current_var_state, action_idx);
            next_action_idx = current_action_idx + 1;
            next_var_state_idx = current_var_state_idx + STATE_LENGTH_HEU;
            if (next_action_idx < STORAGE_LENGTH) {
                actions[next_action_idx] = action_idx;
            } else {
                printf("Error. Out of memory for actions.\n");
                free_storage();
                abort();
            }
        }

        uint64_t* next_var_state;
        if (next_var_state_idx < 0) {
            next_var_state = INITIAL_STATE;
        } else {
            next_var_state = get_state(next_var_state_idx);
        }

        if (is_goal(next_var_state)) {
            current_action_idx = next_action_idx;
            printf("Success.\n");
            done = true;
            break;
        }

        ff_heuristic(next_var_state);
        uint64_t next_value = next_var_state[STATE_LENGTH];

        uint64_t prob = exp(-(next_value - value) / T);
        std::bernoulli_distribution d(prob);
        if (prob >= 1 || d(rng)) {
            current_var_state_idx = next_var_state_idx;
            current_action_idx = next_action_idx;
            value = next_value;
            current_var_state = next_var_state;

            // update storage in case we remove actions/states
            if (drop) {
                remove_batch(n_states_to_drop);
                actions_size -= n_states_to_drop;
                storage_size -= n_states_to_drop * STATE_LENGTH_HEU;
            } else {
                actions_size++;
                storage_size += STATE_LENGTH_HEU;
            }
        } else {
            // if we tried moving forward, then clean up the "draft" storage used
            if (next_action_idx > current_action_idx) {
                remove_last();
            }
        }

        if (current_action_idx + 1 != actions_size ||
            current_var_state_idx + STATE_LENGTH_HEU != storage_size ||
            actions_size * STATE_LENGTH_HEU != storage_size
        ) {
            printf("action: %d + 1 == %d, storage: %d + %d == %d, action_size and storage_size: %d * %d == %d\n",
                current_action_idx, actions_size, current_var_state_idx, STATE_LENGTH_HEU, storage_size, actions_size, STATE_LENGTH_HEU, storage_size);
            free_storage();
            abort();
        }

        sa_count++;
        T *= u;
    }

    auto now = std::chrono::steady_clock::now();
    std::chrono::duration<double> total = now - start;
    printf("number of states created: %ld\n", sa_count);
    printf("time elapsed: %f\n", total.count());
    printf("number of states created per second: %f\n", sa_count / total.count());
    printf("\n");

    if (!done) {
        printf("No solution found.\n");
    } else {
        for (int i = 0; i <= current_action_idx; i++) {
            printf("%d\n", actions[i]);
        }
    }

    free_storage();
}