#include "storage.h"

typedef struct {
    uint64_t* storage_ptr;
    uint64_t* last_ptr;
    size_t size;
} Storage;

Storage storage;

void storage_init() {
    uint64_t* storage_ptr = (uint64_t*) malloc(sizeof(uint64_t) * STORAGE_LENGTH);
    if (storage_ptr == NULL) {
        printf("Error: storage allocation failed.\n");
        abort();
    }
    storage.storage_ptr = storage_ptr;
    storage.last_ptr = NULL;
    storage.size = 0;
}

uint64_t* allocate_state() {
    if (storage.size + STATE_LENGTH_HEU > STORAGE_LENGTH) {
        printf("Storage is full.\n");
        exit(EXIT_FAILURE);
    }
    storage.size += STATE_LENGTH_HEU;
    // if there is nothing in the storage yet then the last ptr is at the beginning,
    // otherwise, it is incremented by the state length
    storage.last_ptr = (storage.last_ptr) ? storage.last_ptr + STATE_LENGTH_HEU : storage.storage_ptr;

    count++;
    return storage.last_ptr;
}

void remove_last() {
    if (storage.size == 0) {
        return;
    }
    storage.last_ptr -= STATE_LENGTH_HEU;
    storage.size -= STATE_LENGTH_HEU;
}

void free_storage() {
    free(storage.storage_ptr);
}

uint64_t count = 0;