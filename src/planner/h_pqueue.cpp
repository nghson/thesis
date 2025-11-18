#include "h_pqueue.h"

void add_to_queue(uint64_t* state, uint64_t* prev_state, int action_idx, PlannerQueue& pq, PathInfoMap& path_info) {
    if (!contain_visited(state)) {
        ff_heuristic(state);
        path_info.insert({state, std::make_pair(prev_state, action_idx)});
        pq.push(state);
    } else {
        remove_last();
    }
}
