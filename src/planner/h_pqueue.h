#ifndef QUEUE_H
#define QUEUE_H

#include <stdint.h>
#include <queue>
#include <unordered_map>
#include <utility>
#include "config.h"
#include "visited_set.h"
#include "storage.h"
#include "ff_heuristic.h"

 struct CompareState {
     bool operator()(uint64_t* left, uint64_t* right) {
         return left[STATE_LENGTH] > right[STATE_LENGTH];
     }
 }; 

typedef std::priority_queue<uint64_t*, std::vector<uint64_t*>, CompareState> PlannerQueue;
typedef std::unordered_map<uint64_t*, std::pair<uint64_t*, int>> PathInfoMap;


void add_to_queue(uint64_t* state, uint64_t* prev_state, int action_idx, PlannerQueue& pq, PathInfoMap& path_info);

#endif
