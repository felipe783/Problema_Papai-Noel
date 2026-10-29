/*
 * elfo.c — thread de um elfo (um pedido por elfo, versão finita).
 *
 * Formação de grupos por fila de grupos com ids: o elfo só entra no grupo
 * ABERTO (grupo_aberto). Quem completa o 3º lugar fecha o grupo, avança
 * grupo_aberto e acorda Noel. Como inscrição e fechamento acontecem dentro
 * do mesmo mutex, nenhum elfo consegue entrar num grupo fechado ou em
 * atendimento: os seguintes já caem no próximo grupo.
 */
#include "comum.h"

#include "elfo.h"
#include "tempo.h"

void *thread_elfo(void *arg)
{
    ArgElfo *a = arg;
    Oficina *o = a->o;
    int id = a->id;

    pthread_mutex_lock(&o->mutex);
    esperar_largada(o);
    pthread_mutex_unlock(&o->mutex);

    dormir_ate_ms(o, o->cfg->elfo0_ms + id); /* simula a chegada */

    pthread_mutex_lock(&o->mutex);
    if (o->abortar) {
        pthread_mutex_unlock(&o->mutex);
        return NULL;
    }
    o->t_pedido[id] = ms_desde_inicio(o);

    int g = o->grupo_aberto;
    Grupo *gr = &o->grupos[g];
    if (gr->estado != GRUPO_ABERTO || gr->n >= TAM_GRUPO) {
        o->violacoes_regras++; /* invasão de grupo fechado */
        pthread_mutex_unlock(&o->mutex);
        return NULL;
    }
    gr->membros[gr->n++] = id;
    o->grupo_do_elfo[id] = g;
    registrar(o, PART_ELFO, id, EV_CHEGADA, g + 1);

    if (gr->n == TAM_GRUPO) {
        /* 3º elfo: fecha o grupo e o coloca na fila de Noel. */
        gr->estado = GRUPO_PRONTO;
        gr->t_pronto = o->t_pedido[id];
        o->grupos_fechados++;
        if (o->grupo_aberto + 1 < o->n_grupos)
            o->grupo_aberto++;
        registrar(o, PART_ELFO, id, EV_GRUPO_PRONTO, g + 1);
        pthread_cond_signal(&o->cv_noel);
    }

    /* Espera Noel terminar a ajuda deste grupo (ou o timeout). */
    while (gr->estado != GRUPO_CONCLUIDO && !o->abortar)
        pthread_cond_wait(&o->cv_elfos, &o->mutex);
    pthread_mutex_unlock(&o->mutex);
    return NULL;
}
