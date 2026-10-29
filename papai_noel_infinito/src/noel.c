/*
 * noel.c — thread do Papai Noel, em laço infinito.
 *
 * Noel dorme em cv_noel até haver (a) as 9 renas no estábulo ou (b) um
 * grupo fechado de 3 elfos na fila. A decisão é tomada com o mutex
 * adquirido e as renas têm prioridade. Preparação, viagem e ajuda são
 * simuladas fora do mutex; durante elas ninguém mais decide nada por Noel.
 * O laço só termina no encerramento (Ctrl+C, comando "sair" ou --duracao-s).
 */
#include "comum.h"

#include "atores.h"
#include "relogio.h"
#include "saida.h"

/* Simula `ms` fora do mutex. Entra e sai com o mutex adquirido. */
static void trabalhar_fora_do_mutex(Oficina *o, int ms)
{
    pthread_mutex_unlock(&o->mutex);
    relogio_dormir(o->rel, ms);
    pthread_mutex_lock(&o->mutex);
}

static void fazer_viagem(Oficina *o, int disputa)
{
    if (o->renas_estabulo != NUM_RENAS)
        o->violacoes++; /* viagem sem as 9 renas */

    double t_ini = relogio_agora(o->rel);
    double resposta = t_ini - o->t_nona;
    o->resposta_soma += resposta;
    if (resposta > o->resposta_max)
        o->resposta_max = resposta;

    o->noel = NOEL_PREPARANDO;
    for (int i = 0; i < NUM_RENAS; i++)
        o->rena[i] = RENA_ATRELADA;
    emitir(o, "noel", 0, "inicio_preparo", 0,
           "Noel acorda com as 9 renas%s e atrela o trenó (viagem %d)",
           disputa ? " (havia elfos esperando: renas têm prioridade)" : "",
           o->viagens_concluidas + 1);
    trabalhar_fora_do_mutex(o, o->cfg->preparo_ms);

    o->noel = NOEL_VIAJANDO;
    for (int i = 0; i < NUM_RENAS; i++)
        o->rena[i] = RENA_VIAJANDO;
    emitir(o, "noel", 0, "partida", 0, "Trenó parte para entregar os presentes (viagem %d)",
           o->viagens_concluidas + 1);
    trabalhar_fora_do_mutex(o, o->cfg->viagem_ms);

    o->ocupado_ms += relogio_agora(o->rel) - t_ini;
    o->viagens_concluidas++;
    o->renas_estabulo = 0;
    for (int i = 0; i < NUM_RENAS; i++)
        o->rena[i] = RENA_FERIAS;
    o->noel = NOEL_DORMINDO;
    emitir(o, "noel", 0, "fim_viagem", 0,
           "Viagem %d concluída: as renas saem de férias e Noel volta a dormir",
           o->viagens_concluidas);
    pthread_cond_broadcast(&o->cv_renas); /* libera as 9 renas */
}

static void ajudar_grupo(Oficina *o)
{
    if (o->renas_estabulo == NUM_RENAS)
        o->violacoes++; /* prioridade violada: renas prontas esperando */

    int id = o->proximo_grupo++;
    Grupo *g = GRUPO(o, id);
    if (g->n != TAM_GRUPO)
        o->violacoes++; /* grupo com != 3 elfos */

    double t_ini = relogio_agora(o->rel);
    o->noel = NOEL_AJUDANDO;
    o->grupo_em_ajuda = id;
    o->n_ultimas = g->n;
    for (int k = 0; k < g->n; k++) {
        int e = g->membros[k];
        double espera = t_ini - o->t_pedido[e];
        o->ultimas_esperas[k] = espera;
        o->espera_soma += espera;
        o->espera_n++;
        if (espera > o->espera_max)
            o->espera_max = espera;
        o->elfo[e] = ELFO_SENDO_AJUDADO;
    }
    emitir(o, "noel", 0, "inicio_ajuda", id, "Noel ajuda o grupo %d (elfos %d, %d, %d)",
           id, g->membros[0], g->membros[1], g->membros[2]);
    trabalhar_fora_do_mutex(o, o->cfg->ajuda_ms);

    o->ocupado_ms += relogio_agora(o->rel) - t_ini;
    o->grupos_atendidos++;
    o->ultimo_concluido = id;
    o->grupo_em_ajuda = 0;
    for (int k = 0; k < g->n; k++) {
        o->elfo[g->membros[k]] = ELFO_TRABALHANDO;
        o->grupo_do_elfo[g->membros[k]] = 0;
    }
    o->noel = NOEL_DORMINDO;
    emitir(o, "noel", 0, "fim_ajuda", id, "Grupo %d atendido: os elfos voltam ao trabalho", id);
    pthread_cond_broadcast(&o->cv_elfos); /* cada elfo confere se é o seu grupo */
}

void *thread_noel(void *arg)
{
    Oficina *o = ((ArgAtor *)arg)->o;

    pthread_mutex_lock(&o->mutex);
    while (!o->encerrar) {
        while (!o->encerrar && o->renas_estabulo < NUM_RENAS &&
               o->proximo_grupo == o->grupo_aberto)
            pthread_cond_wait(&o->cv_noel, &o->mutex);
        if (o->encerrar)
            break;

        int renas = o->renas_estabulo == NUM_RENAS;
        int elfos = o->proximo_grupo < o->grupo_aberto;
        if (renas) { /* prioridade às renas */
            if (elfos)
                o->disputas++;
            fazer_viagem(o, elfos);
        } else {
            ajudar_grupo(o);
        }
    }
    o->noel = NOEL_ENCERRADO;
    emitir(o, "noel", 0, "encerrado", 0, "Simulação encerrada");
    pthread_mutex_unlock(&o->mutex);
    return NULL;
}
