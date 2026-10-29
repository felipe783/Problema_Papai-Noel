/*
 * rena.c — thread de uma rena (uma viagem, versão finita).
 *
 * Cada rena chega em renas_ms, incrementa o contador e, se for a 9ª,
 * registra o instante e acorda Noel. Depois espera o fim da preparação.
 */
#include "comum.h"

#include "rena.h"
#include "tempo.h"

void *thread_rena(void *arg)
{
    ArgRena *a = arg;
    Oficina *o = a->o;

    pthread_mutex_lock(&o->mutex);
    esperar_largada(o);
    pthread_mutex_unlock(&o->mutex);

    dormir_ate_ms(o, o->cfg->renas_ms); /* simula a chegada */

    pthread_mutex_lock(&o->mutex);
    if (o->abortar) {
        pthread_mutex_unlock(&o->mutex);
        return NULL;
    }
    o->renas_prontas++;
    registrar(o, PART_RENA, a->id, EV_CHEGADA, 0);
    if (o->renas_prontas == NUM_RENAS) {
        o->t_nona = ms_desde_inicio(o);
        registrar(o, PART_RENA, a->id, EV_NONA_RENA, 0);
        pthread_cond_signal(&o->cv_noel);
    }

    while (!o->viagem_concluida && !o->abortar)
        pthread_cond_wait(&o->cv_renas, &o->mutex);
    pthread_mutex_unlock(&o->mutex);
    return NULL;
}
