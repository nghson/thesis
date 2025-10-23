#ifndef VISITED_H
#define VISITED_H

#include <stdint.h>
#include <unordered_set>
#include "./xxHash/xxhash.h"
#include "config.h"

void insert_visited(const uint64_t* state_bitrep);
bool contain_visited(const uint64_t* state_bitrep);

#endif