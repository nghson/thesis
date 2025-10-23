#ifndef FF_GRAPH_H
#define FF_GRAPH_H

#include <stdint.h>
#include <vector>

void convert_state_to_multi_valued(uint64_t* state, uint64_t* ff_state, std::vector<int>& fact_membership);
bool is_ff_goal(uint64_t* ff_state);
void build_next_layer(uint64_t* next_state, const uint64_t* state, std::vector<int>& fact_membership, std::vector<int>& action_membership, std::vector<int>& achieving_action, int layer, std::vector<std::vector<int>>& G);
std::vector<int> get_preconds_for_action(int action_idx);
std::vector<int> get_effects_for_action(int action_idx);
void backward(std::vector<int>& fact_membership, std::vector<int>& action_membership, std::vector<int>& achieving_action, int layer, uint64_t* h);

#endif