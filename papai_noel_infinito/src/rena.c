/*
 * rena.c — thread de uma rena: férias -> estábulo -> viagem -> férias ...
 *
 * A rena que completa 9 no estábulo acorda Noel. Todas esperam em cv_renas
 * até a viagem da qual fazem parte terminar (predicado sobre
 * viagens_concluidas, imune a acordar espúrio e a aviso perdido).
 */
#include "comum.h"

#include "atores.h"
#include "relogio.h"
#include "saida.h"

void *thread_rena(void *arg)
{
    ArgAtor *a = arg;
    Oficina *o = a->o;
    const Config *c = o->cfg;

    for (;;) {
        relogio_dormir(o->rel, sortear(&a->semente, c->ferias_min, c->ferias_max)); /* férias */

        pthread_mutex_lock(&o->mutex);
        if (o->encerrar) {
            pthread_mutex_unlock(&o->mutex);
            break;
        }
        int minha_viagem = o->viagens_concluidas + 1;
        o->rena[a->id] = RENA_ESTABULO;
        o->renas_estabulo++;
        if (o->renas_estabulo == NUM_RENAS) {
            o->t_nona = relogio_agora(o->rel);
            emitir(o, "rena", a->id, "nona_rena", 0,
                   "Rena %d é a 9ª a voltar e acorda o Noel", a->id);
            pthread_cond_signal(&o->cv_noel);
        } else {
            emitir(o, "rena", a->id, "rena_chegou", 0, "Rena %d voltou das férias (%d/9 no estábulo)",
                   a->id, o->renas_estabulo);
        }

        while (!o->encerrar && o->viagens_concluidas < minha_viagem)
            pthread_cond_wait(&o->cv_renas, &o->mutex);
        int sair = o->encerrar;
        pthread_mutex_unlock(&o->mutex);
        if (sair)
            break;
    }
    return NULL;
}
