/* tempo.h — relógio monotônico e sleeps que SIMULAM chegada/ajuda/viagem. */
#ifndef TEMPO_H
#define TEMPO_H

#include "comum.h"

/* Instante atual (CLOCK_MONOTONIC). */
struct timespec agora(void);

/* t + ms (ms pode ser fracionário). */
struct timespec somar_ms(struct timespec t, double ms);

/* (b - a) em milissegundos. */
double diff_ms(struct timespec a, struct timespec b);

/* Milissegundos desde o sinal de início. */
double ms_desde_inicio(const Oficina *o);

/* Dorme até t0 + ms (sleep absoluto: não acumula atraso). */
void dormir_ate_ms(const Oficina *o, double ms);

#endif
