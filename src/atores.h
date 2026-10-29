#ifndef ATORES_H
#define ATORES_H

#include "comum.h"

typedef struct {
    Oficina *o;
    int id;
    unsigned semente; /* rand_r: cada thread tem a sua */
} ArgAtor;

void *thread_noel(void *arg);
void *thread_rena(void *arg);
void *thread_elfo(void *arg);

/* Sorteia um inteiro em [min, max]. */
int sortear(unsigned *semente, int min, int max);

#endif
