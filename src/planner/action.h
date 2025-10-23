#ifndef ACTION_H
#define ACTION_H

#include <stdint.h>
#include <unordered_map>
#include <utility>
#include "config.h"
#include "storage.h"
#include "h_pqueue.h"

void actions(uint64_t* state_bitrep, PlannerQueue& pq, std::unordered_map<uint64_t*, std::pair<uint64_t*, int>>& path_info);
bool is_goal(uint64_t* state_bitrep);
extern uint64_t INITIAL_STATE[STATE_LENGTH_HEU];

#endif