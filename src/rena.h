/* rena.h — threads das renas. */
#ifndef RENA_H
#define RENA_H

#include "comum.h"

typedef struct {
    Oficina *o;
    int id; /* 1..9 */
} ArgRena;

void *thread_rena(void *arg);

#endif
