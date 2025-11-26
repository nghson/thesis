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
    std::vector<int> actions;

    double T = 10000;
    double u = 0.995;
    uint64_t value;
    bool done = false;

    while (T > 1) {
        // next state

        uint64_t* last_state = get_last_state();

        // check goal
        if (is_goal(last_state)) {
            printf("Success.\n");
            // complete action array
            done = true;
            break;
        }

        // state value
        ff_heuristic(last_state);
        uint64_t next_value = actions.size() + last_state[STATE_LENGTH];

        // update state
        if (next_value < value) {
            // keep the state and add the action, or remove states and actions 
            
            // update value
            value = next_value;
        } else {
            // undo the last action whether it's adding a new state or removing some states
        }
        std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
        std::bernoulli_distribution();


        T *= u;
    }

    if (!done) {
        printf("No solution found.\n");
    }

    free_storage();
}