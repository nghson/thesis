#include "h_pqueue.h"

void add_to_queue(uint64_t* state, PlannerQueue& pq) {
    if (!contain_visited(state)) {
        ff_heuristic(state);
        pq.push(state);
    } else {
        remove_last();
    }
}
