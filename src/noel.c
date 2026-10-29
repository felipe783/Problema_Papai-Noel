/*
 * noel.c — thread do Papai Noel.
 *
 * Noel dorme em cv_noel até haver (a) as 9 renas prontas e a viagem ainda
 * não feita, ou (b) um grupo fechado de 3 elfos na fila. A decisão é tomada
 * com o mutex adquirido: renas primeiro. A ajuda/preparação é simulada fora
 * do mutex e nunca é interrompida (só a própria thread de Noel decide).
 * O laço termina quando a viagem e todos os grupos foram concluídos, ou no
 * timeout de segurança, que marca `abortar` e acorda todo mundo.
 */
#include "comum.h"

#include <errno.h>

#include "noel.h"
#include "tempo.h"

/* Prepara a viagem. Entra e sai com o mutex adquirido. */
static void preparar_viagem(Oficina *o)
{
    if (o->renas_prontas < NUM_RENAS)
        o->violacoes_regras++; /* viagem com menos de 9 renas */

    o->viagem_iniciada = 1;
    o->estado = NOEL_PREPARANDO;
    o->ajuda_em_curso = 1;
    o->t_ini_preparo = ms_desde_inicio(o);
    registrar(o, PART_NOEL, 0, EV_INICIO_PREPARACAO, 0);
    double inicio = o->t_ini_preparo;

    pthread_mutex_unlock(&o->mutex);
    dormir_ate_ms(o, inicio + o->cfg->preparo_ms); /* simula a preparação */
    pthread_mutex_lock(&o->mutex);

    o->t_fim_preparo = ms_desde_inicio(o);
    o->ocupado_ms += o->t_fim_preparo - o->t_ini_preparo;
    o->viagem_concluida = 1;
    o->ajuda_em_curso = 0;
    o->estado = NOEL_DORMINDO;
    registrar(o, PART_NOEL, 0, EV_FIM_PREPARACAO, 0);
    pthread_cond_broadcast(&o->cv_renas); /* libera as renas */
}

/* Ajuda o grupo g. Entra e sai com o mutex adquirido. */
static void ajudar_grupo(Oficina *o, int g)
{
    Grupo *gr = &o->grupos[g];
    if (gr->n != TAM_GRUPO || gr->estado != GRUPO_PRONTO)
        o->violacoes_regras++; /* grupo atendido com != 3 elfos */

    gr->estado = GRUPO_EM_AJUDA;
    o->estado = NOEL_AJUDANDO;
    o->ajuda_em_curso = 1;
    gr->t_inicio = ms_desde_inicio(o);
    for (int k = 0; k < gr->n; k++)
        o->t_inicio_ajuda[gr->membros[k]] = gr->t_inicio;
    registrar(o, PART_NOEL, 0, EV_INICIO_AJUDA, g + 1);
    double inicio = gr->t_inicio;

    pthread_mutex_unlock(&o->mutex);
    dormir_ate_ms(o, inicio + o->cfg->ajuda_ms); /* simula a ajuda */
    pthread_mutex_lock(&o->mutex);

    gr->t_fim = ms_desde_inicio(o);
    o->ocupado_ms += gr->t_fim - gr->t_inicio;
    for (int k = 0; k < gr->n; k++)
        o->atendimentos[gr->membros[k]]++;
    gr->estado = GRUPO_CONCLUIDO;
    o->grupos_concluidos++;
    o->ajuda_em_curso = 0;
    o->estado = NOEL_DORMINDO;
    registrar(o, PART_NOEL, 0, EV_FIM_AJUDA, g + 1);
    pthread_cond_broadcast(&o->cv_elfos); /* libera os 3 elfos do grupo */
}

void *thread_noel(void *arg)
{
    Oficina *o = arg;
    const Config *c = o->cfg;

    pthread_mutex_lock(&o->mutex);
    esperar_largada(o);
    struct timespec limite = somar_ms(o->t0, c->timeout_ms);

    for (;;) {
        if (o->viagem_concluida && o->grupos_concluidos == o->n_grupos)
            break; /* as duas demandas terminaram */

        int renas_ok = o->renas_prontas == NUM_RENAS && !o->viagem_iniciada;
        int elfos_ok = o->proximo_grupo < o->grupos_fechados;

        /* Teste de prioridade: Noel fica "atrasado" até as duas demandas
         * estarem prontas ao mesmo tempo (espera em cond var, sem sleep). */
        int liberado = 1;
        if (c->teste_prioridade && !o->noel_liberado) {
            liberado = renas_ok && elfos_ok;
            o->noel_liberado = liberado;
        }

        if (!liberado || (!renas_ok && !elfos_ok)) {
            int rc = pthread_cond_timedwait(&o->cv_noel, &o->mutex, &limite);
            if (rc == ETIMEDOUT) {
                o->abortar = 1;
                registrar(o, PART_NOEL, 0, EV_TIMEOUT, 0);
                break;
            }
            continue; /* acordou: reavalia as condições */
        }

        /* Decisão, com o mutex adquirido. */
        if (o->ajuda_em_curso)
            o->violacoes_regras++; /* decidiria no meio de uma ajuda */
        o->decisoes++;
        if (renas_ok && elfos_ok)
            o->decisoes_com_disputa++;

        int escolhe_renas = c->ingenua ? !elfos_ok : renas_ok;
        if (!escolhe_renas && renas_ok)
            o->violacoes_prioridade++; /* elfos com as 9 renas prontas */
        if (o->primeira_decisao == 0)
            o->primeira_decisao = escolhe_renas ? 1 : 2;

        if (escolhe_renas) {
            o->estado = NOEL_PREPARANDO;
            registrar(o, PART_NOEL, 0, EV_DECISAO, 0);
            preparar_viagem(o);
        } else {
            int g = o->proximo_grupo++;
            o->estado = NOEL_AJUDANDO;
            registrar(o, PART_NOEL, 0, EV_DECISAO, g + 1);
            ajudar_grupo(o, g);
        }
    }

    if (!o->abortar) {
        o->estado = NOEL_ENCERRADO;
        o->t_encerramento = ms_desde_inicio(o);
        registrar(o, PART_NOEL, 0, EV_ENCERRAMENTO, 0);
    } else {
        o->t_encerramento = ms_desde_inicio(o);
    }
    /* Ninguém pode ficar bloqueado: acorda todas as filas. */
    pthread_cond_broadcast(&o->cv_elfos);
    pthread_cond_broadcast(&o->cv_renas);
    pthread_mutex_unlock(&o->mutex);
    return NULL;
}
