/*
 * elfo.c — thread de um elfo: trabalha -> pede ajuda -> é ajudado -> ...
 *
 * Os grupos formam uma fila com ids crescentes. O elfo entra no grupo
 * aberto; o 3º fecha o grupo NA MESMA seção crítica em que se inscreve e
 * abre o próximo, então nenhum elfo invade um grupo fechado. Noel atende
 * em ordem FIFO, e cada elfo espera até `ultimo_concluido >= seu grupo`.
 */
#include "comum.h"

#include <stdlib.h>

#include "atores.h"
#include "relogio.h"
#include "saida.h"

int sortear(unsigned *semente, int min, int max)
{
    if (max <= min)
        return min;
    return min + rand_r(semente) % (max - min + 1);
}

void *thread_elfo(void *arg)
{
    ArgAtor *a = arg;
    Oficina *o = a->o;
    const Config *c = o->cfg;

    for (;;) {
        relogio_dormir(o->rel, sortear(&a->semente, c->trabalho_min, c->trabalho_max)); /* trabalho */

        pthread_mutex_lock(&o->mutex);
        if (o->encerrar) {
            pthread_mutex_unlock(&o->mutex);
            break;
        }
        int meu = o->grupo_aberto;
        Grupo *g = GRUPO(o, meu);
        g->membros[g->n++] = a->id;
        o->grupo_do_elfo[a->id] = meu;
        o->t_pedido[a->id] = relogio_agora(o->rel);
        o->pedidos++;

        if (g->n == TAM_GRUPO) { /* fecha o grupo e abre o próximo */
            for (int k = 0; k < TAM_GRUPO; k++)
                o->elfo[g->membros[k]] = ELFO_NA_FILA;
            g->t_pronto = o->t_pedido[a->id];
            o->grupo_aberto++;
            if (o->grupo_aberto - o->proximo_grupo >= CAP_GRUPOS)
                o->violacoes++; /* não acontece com MAX_ELFOS: proteção do anel */
            Grupo *novo = GRUPO(o, o->grupo_aberto);
            novo->id = o->grupo_aberto;
            novo->n = 0;
            emitir(o, "elfo", a->id, "grupo_formado", meu,
                   "Elfo %d completa o grupo %d (%d, %d, %d) e entra na fila do Noel",
                   a->id, meu, g->membros[0], g->membros[1], g->membros[2]);
            pthread_cond_signal(&o->cv_noel);
        } else {
            o->elfo[a->id] = ELFO_ESPERANDO;
            emitir(o, "elfo", a->id, "pede_ajuda", meu, "Elfo %d precisa de ajuda (grupo %d: %d/3)",
                   a->id, meu, g->n);
        }

        while (!o->encerrar && o->ultimo_concluido < meu)
            pthread_cond_wait(&o->cv_elfos, &o->mutex);
        int sair = o->encerrar;
        pthread_mutex_unlock(&o->mutex);
        if (sair)
            break;
    }
    return NULL;
}
