/*
 * tempo.c — medição com CLOCK_MONOTONIC.
 *
 * Os sleeps daqui servem SOMENTE para simular a duração das atividades
 * (chegada, ajuda, preparação). Nenhuma sincronização depende deles:
 * a coordenação entre threads é feita por mutex e variáveis de condição.
 */
#include "comum.h"

#include <errno.h>

#include "tempo.h"

struct timespec agora(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t;
}

struct timespec somar_ms(struct timespec t, double ms)
{
    long long ns = (long long)(ms * 1e6);
    t.tv_sec += (time_t)(ns / 1000000000LL);
    t.tv_nsec += (long)(ns % 1000000000LL);
    if (t.tv_nsec >= 1000000000L) {
        t.tv_sec += 1;
        t.tv_nsec -= 1000000000L;
    }
    return t;
}

double diff_ms(struct timespec a, struct timespec b)
{
    return (double)(b.tv_sec - a.tv_sec) * 1e3 + (double)(b.tv_nsec - a.tv_nsec) / 1e6;
}

double ms_desde_inicio(const Oficina *o)
{
    return diff_ms(o->t0, agora());
}

void dormir_ate_ms(const Oficina *o, double ms)
{
    struct timespec alvo = somar_ms(o->t0, ms);
    /* clock_nanosleep (família nanosleep) com TIMER_ABSTIME; repete se
     * for interrompido por sinal. */
    while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &alvo, NULL) == EINTR) {
    }
}
