#ifndef STORAGE_H
#define STORAGE_H

#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include "config.h"

void storage_init();
uint64_t* allocate_state();
void remove_last();
void free_storage();

uint64_t* get_state(int index);
void remove_batch(int n);

extern uint64_t count;

#endif