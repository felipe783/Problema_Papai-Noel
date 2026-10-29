/* elfo.h — threads dos elfos. */
#ifndef ELFO_H
#define ELFO_H

#include "comum.h"

typedef struct {
    Oficina *o;
    int id; /* 0..elfos-1; chega em elfo0_ms + id */
} ArgElfo;

void *thread_elfo(void *arg);

#endif
