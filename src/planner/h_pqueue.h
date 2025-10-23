#ifndef QUEUE_H
#define QUEUE_H

#include <stdint.h>
#include <queue>
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

void add_to_queue(uint64_t* state, PlannerQueue& pq);

#endif
