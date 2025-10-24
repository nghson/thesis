#include <stdint.h>
#include <stdio.h>

#include <chrono>
#include <cstdint>
#include <queue>
#include <utility>
#include <unordered_map>
#include <stack>

#include "storage.h"
#include "visited_set.h"
#include "action.h"
#include "h_pqueue.h"

int main() {
    storage_init();

    PlannerQueue pq;
    add_to_queue(INITIAL_STATE, pq);

    PathInfoMap path_info;

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
        return 0;
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

    return 0;
}
