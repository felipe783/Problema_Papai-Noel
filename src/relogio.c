/*
 * relogio.c — relógio virtual com pausa e velocidade.
 *
 * tempo_virtual = virt_base + (agora_real - real_base) * velocidade
 * Ao pausar ou mudar a velocidade, a base é refeita, então o tempo virtual
 * nunca salta. Os sleeps daqui só simulam durações: nenhuma coordenação
 * entre Noel, renas e elfos depende deles.
 */
#include "comum.h"

#include <errno.h>

#include "relogio.h"

#define FATIA_MS 25.0 /* granularidade do sono: reage a pausa/encerramento */

static struct timespec real_agora(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t;
}

static double diff_ms(struct timespec a, struct timespec b)
{
    return (double)(b.tv_sec - a.tv_sec) * 1e3 + (double)(b.tv_nsec - a.tv_nsec) / 1e6;
}

/* Chamada com r->m adquirido. */
static double virt_locked(Relogio *r)
{
    if (r->pausado)
        return r->virt_base;
    return r->virt_base + diff_ms(r->real_base, real_agora()) * r->velocidade;
}

static void rebase_locked(Relogio *r)
{
    r->virt_base = virt_locked(r);
    r->real_base = real_agora();
}

void relogio_iniciar(Relogio *r, double velocidade)
{
    pthread_mutex_init(&r->m, NULL);
    pthread_cond_init(&r->cv, NULL);
    r->pausado = 0;
    r->encerrar = 0;
    r->velocidade = velocidade;
    r->virt_base = 0;
    r->real_base = real_agora();
}

double relogio_agora(Relogio *r)
{
    pthread_mutex_lock(&r->m);
    double v = virt_locked(r);
    pthread_mutex_unlock(&r->m);
    return v;
}

void relogio_pausar(Relogio *r, int pausar)
{
    pthread_mutex_lock(&r->m);
    if (pausar != r->pausado) {
        rebase_locked(r);
        r->pausado = pausar;
        pthread_cond_broadcast(&r->cv);
    }
    pthread_mutex_unlock(&r->m);
}

void relogio_velocidade(Relogio *r, double v)
{
    pthread_mutex_lock(&r->m);
    rebase_locked(r);
    r->velocidade = v;
    pthread_mutex_unlock(&r->m);
}

void relogio_encerrar(Relogio *r)
{
    pthread_mutex_lock(&r->m);
    r->encerrar = 1;
    pthread_cond_broadcast(&r->cv);
    pthread_mutex_unlock(&r->m);
}

void relogio_estado(Relogio *r, int *pausado, double *velocidade)
{
    pthread_mutex_lock(&r->m);
    *pausado = r->pausado;
    *velocidade = r->velocidade;
    pthread_mutex_unlock(&r->m);
}

void relogio_dormir(Relogio *r, double ms)
{
    pthread_mutex_lock(&r->m);
    double alvo = virt_locked(r) + ms;
    for (;;) {
        while (r->pausado && !r->encerrar)
            pthread_cond_wait(&r->cv, &r->m); /* pausa sem espera ocupada */
        double falta = alvo - virt_locked(r);
        if (r->encerrar || falta <= 0)
            break;
        double real = falta / r->velocidade;
        if (real > FATIA_MS)
            real = FATIA_MS;
        pthread_mutex_unlock(&r->m);

        long long ns = (long long)(real * 1e6);
        struct timespec d = { (time_t)(ns / 1000000000LL), (long)(ns % 1000000000LL) };
        while (nanosleep(&d, &d) == -1 && errno == EINTR) {
        }
        pthread_mutex_lock(&r->m);
    }
    pthread_mutex_unlock(&r->m);
}
