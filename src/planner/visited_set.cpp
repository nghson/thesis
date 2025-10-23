#include "visited_set.h"

std::unordered_set<uint64_t> visited;

void insert_visited(const uint64_t* state_bitrep) {
    XXH64_hash_t hash = XXH3_64bits(state_bitrep, STATE_LENGTH * sizeof(uint64_t));
    visited.insert(hash);
}

bool contain_visited(const uint64_t* state_bitrep) {
    XXH64_hash_t hash = XXH3_64bits(state_bitrep, STATE_LENGTH * sizeof(uint64_t));
    return visited.count(hash) == 1;
}