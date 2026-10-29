/*
 * main.c — Tema 11: Problema do Papai Noel (versão finita), C11 + pthreads.
 *
 * Fluxo: lê argumentos -> inicializa mecanismos -> cria 1 Noel, 9 renas e
 * N elfos (todas antes de qualquer join) -> espera todas ficarem prontas ->
 * marca t0 (CLOCK_MONOTONIC) e dá o sinal de início -> joins -> destrói os
 * mecanismos -> calcula métricas -> exporta CSVs -> imprime um resumo.
 *
 * Uso: ./simulacao --elfos 6 --renas-ms 10 --rep 1 --semente 11 --out dados/
 *                  [--teste-prioridade] [--ingenua] [--timeout-ms 2000]
 */
#include "comum.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "csv.h"
#include "elfo.h"
#include "metricas.h"
#include "noel.h"
#include "rena.h"
#include "tempo.h"

void esperar_largada(Oficina *o)
{
    o->threads_prontas++;
    pthread_cond_broadcast(&o->cv_largada); /* avisa a main */
    while (!o->largada)
        pthread_cond_wait(&o->cv_largada, &o->mutex);
}

void registrar(Oficina *o, TipoParticipante tipo, int participante,
               TipoEvento ev, int grupo_id)
{
    if (o->n_eventos >= o->cap_eventos) {
        o->eventos_perdidos++;
        return;
    }
    Evento *e = &o->eventos[o->n_eventos++];
    e->t_ms = ms_desde_inicio(o);
    e->participante = participante;
    e->tipo = tipo;
    e->evento = ev;
    e->estado_noel = o->estado;
    e->grupo_id = grupo_id;
}

static void uso(const char *prog)
{
    fprintf(stderr,
            "Uso: %s --elfos N --renas-ms R [opções]\n"
            "  --elfos N          quantidade de elfos, múltiplo de 3 (3..%d)\n"
            "  --renas-ms R       instante de chegada das 9 renas, em ms\n"
            "  --rep K            número da repetição (padrão 1)\n"
            "  --semente S        id registrado da repetição (padrão 11; sem aleatoriedade)\n"
            "  --out DIR          pasta dos CSVs (padrão dados/)\n"
            "  --timeout-ms MS    timeout de segurança do episódio (padrão 2000)\n"
            "  --teste-prioridade Noel só é liberado com renas e grupo prontos\n"
            "  --ingenua          política ingênua (elfos antes das renas), para demonstração\n"
            "  --ajuda-ms, --preparo-ms, --elfo0-ms   durações (padrão 3, 5, 10)\n",
            prog, MAX_ELFOS);
}

static int ler_int(const char *s, int *v)
{
    char *fim;
    long x = strtol(s, &fim, 10);
    if (*s == '\0' || *fim != '\0' || x < 0 || x > 1000000)
        return -1;
    *v = (int)x;
    return 0;
}

static int ler_args(int argc, char **argv, Config *c)
{
    *c = (Config){.elfos = -1, .renas_ms = -1, .rep = 1, .semente = 11, .out = "dados/",
                  .timeout_ms = 2000, .elfo0_ms = 10, .ajuda_ms = 3, .preparo_ms = 5};
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int *alvo = NULL;
        if (!strcmp(a, "--teste-prioridade")) { c->teste_prioridade = 1; continue; }
        if (!strcmp(a, "--ingenua")) { c->ingenua = 1; continue; }
        if (!strcmp(a, "--help") || !strcmp(a, "-h")) return -1;
        if (i + 1 >= argc) { fprintf(stderr, "Falta valor para %s\n", a); return -1; }
        if (!strcmp(a, "--out")) { c->out = argv[++i]; continue; }
        if (!strcmp(a, "--elfos")) alvo = &c->elfos;
        else if (!strcmp(a, "--renas-ms")) alvo = &c->renas_ms;
        else if (!strcmp(a, "--rep")) alvo = &c->rep;
        else if (!strcmp(a, "--semente")) alvo = &c->semente;
        else if (!strcmp(a, "--timeout-ms")) alvo = &c->timeout_ms;
        else if (!strcmp(a, "--ajuda-ms")) alvo = &c->ajuda_ms;
        else if (!strcmp(a, "--preparo-ms")) alvo = &c->preparo_ms;
        else if (!strcmp(a, "--elfo0-ms")) alvo = &c->elfo0_ms;
        else { fprintf(stderr, "Argumento desconhecido: %s\n", a); return -1; }
        if (ler_int(argv[++i], alvo)) { fprintf(stderr, "Valor inválido para %s\n", a); return -1; }
    }
    if (c->elfos < TAM_GRUPO || c->elfos > MAX_ELFOS || c->elfos % TAM_GRUPO) {
        fprintf(stderr, "--elfos deve ser múltiplo de 3 entre 3 e %d\n", MAX_ELFOS);
        return -1;
    }
    if (c->renas_ms < 0) { fprintf(stderr, "--renas-ms é obrigatório\n"); return -1; }
    if (c->timeout_ms < 1) { fprintf(stderr, "--timeout-ms deve ser >= 1\n"); return -1; }
    return 0;
}

static int iniciar_oficina(Oficina *o, const Config *c)
{
    memset(o, 0, sizeof *o);
    o->cfg = c;
    o->n_grupos = c->elfos / TAM_GRUPO;
    o->total_threads = 1 + NUM_RENAS + c->elfos;
    o->estado = NOEL_DORMINDO;
    o->cap_eventos = 4 * c->elfos + 2 * NUM_RENAS + 16;

    o->grupos = calloc((size_t)o->n_grupos, sizeof(Grupo));
    o->t_pedido = malloc(sizeof(double) * (size_t)c->elfos);
    o->t_inicio_ajuda = malloc(sizeof(double) * (size_t)c->elfos);
    o->grupo_do_elfo = malloc(sizeof(int) * (size_t)c->elfos);
    o->atendimentos = calloc((size_t)c->elfos, sizeof(int));
    o->eventos = malloc(sizeof(Evento) * (size_t)o->cap_eventos);
    if (!o->grupos || !o->t_pedido || !o->t_inicio_ajuda || !o->grupo_do_elfo ||
        !o->atendimentos || !o->eventos)
        return -1;
    for (int e = 0; e < c->elfos; e++) {
        o->t_pedido[e] = -1.0;
        o->t_inicio_ajuda[e] = -1.0;
        o->grupo_do_elfo[e] = -1;
    }

    pthread_mutex_init(&o->mutex, NULL);
    pthread_cond_init(&o->cv_largada, NULL);
    pthread_cond_init(&o->cv_elfos, NULL);
    pthread_cond_init(&o->cv_renas, NULL);
    /* cv_noel usa o relógio monotônico, para o timeout de segurança. */
    pthread_condattr_t at;
    pthread_condattr_init(&at);
    pthread_condattr_setclock(&at, CLOCK_MONOTONIC);
    pthread_cond_init(&o->cv_noel, &at);
    pthread_condattr_destroy(&at);
    return 0;
}

static void destruir_oficina(Oficina *o)
{
    pthread_cond_destroy(&o->cv_noel);
    pthread_cond_destroy(&o->cv_renas);
    pthread_cond_destroy(&o->cv_elfos);
    pthread_cond_destroy(&o->cv_largada);
    pthread_mutex_destroy(&o->mutex);
}

static void liberar_oficina(Oficina *o)
{
    free(o->grupos);
    free(o->t_pedido);
    free(o->t_inicio_ajuda);
    free(o->grupo_do_elfo);
    free(o->atendimentos);
    free(o->eventos);
}

int main(int argc, char **argv)
{
    Config c;
    if (ler_args(argc, argv, &c)) {
        uso(argv[0]);
        return 64;
    }

    Oficina o;
    if (iniciar_oficina(&o, &c)) {
        fprintf(stderr, "Sem memória\n");
        return 1;
    }

    pthread_t th_noel, th_renas[NUM_RENAS];
    pthread_t *th_elfos = malloc(sizeof(pthread_t) * (size_t)c.elfos);
    ArgRena arg_renas[NUM_RENAS];
    ArgElfo *arg_elfos = malloc(sizeof(ArgElfo) * (size_t)c.elfos);
    if (!th_elfos || !arg_elfos) {
        fprintf(stderr, "Sem memória\n");
        return 1;
    }

    /* Preparação: cria TODAS as threads antes de qualquer join. */
    if (pthread_create(&th_noel, NULL, thread_noel, &o)) {
        perror("pthread_create");
        return 1;
    }
    for (int r = 0; r < NUM_RENAS; r++) {
        arg_renas[r] = (ArgRena){.o = &o, .id = r + 1};
        if (pthread_create(&th_renas[r], NULL, thread_rena, &arg_renas[r])) {
            perror("pthread_create");
            return 1;
        }
    }
    for (int e = 0; e < c.elfos; e++) {
        arg_elfos[e] = (ArgElfo){.o = &o, .id = e};
        if (pthread_create(&th_elfos[e], NULL, thread_elfo, &arg_elfos[e])) {
            perror("pthread_create");
            return 1;
        }
    }

    /* Sinal de início: só depois que todas estão esperando. */
    pthread_mutex_lock(&o.mutex);
    while (o.threads_prontas < o.total_threads)
        pthread_cond_wait(&o.cv_largada, &o.mutex);
    o.t0 = agora();
    o.largada = 1;
    pthread_cond_broadcast(&o.cv_largada);
    pthread_mutex_unlock(&o.mutex);

    pthread_join(th_noel, NULL);
    for (int r = 0; r < NUM_RENAS; r++)
        pthread_join(th_renas[r], NULL);
    for (int e = 0; e < c.elfos; e++)
        pthread_join(th_elfos[e], NULL);

    /* Mecanismos destruídos só depois de todos os joins. */
    destruir_oficina(&o);

    Metricas m;
    calcular_metricas(&o, &m);
    IdExecucao id;
    montar_id(&c, &id);
    int erro_csv = exportar_csv(&o, &m, &id);

    /* Saída no console somente agora, fora da medição. */
    printf("%s: status=%s T=%.3f ms concluidos=%d/%d vazao=%.2f pedidos/s "
           "espera_p95=%.3f ms resposta_renas=%.3f ms viol_prio=%d viol_regras=%d "
           "decisoes=%d (com disputa: %d) util_noel=%.1f%%\n",
           id.execucao, m.status, m.T_ms, m.concluidos, m.previstos, m.vazao,
           m.espera_p95, m.resposta_renas, m.violacoes_prioridade, m.violacoes_regras,
           o.decisoes, o.decisoes_com_disputa, 100.0 * m.utilizacao);

    int rc = 0;
    if (c.teste_prioridade) {
        int ok1 = o.primeira_decisao == 1;
        int ok2 = m.concluidos == m.previstos;
        int ok3 = m.violacoes_prioridade == 0 && m.violacoes_regras == 0 && !o.abortar;
        int ok4 = o.decisoes_com_disputa >= 1;
        printf("[teste-prioridade] disputa na 1a decisão (renas e grupo prontos): %s\n", ok4 ? "SIM" : "NAO");
        printf("[teste-prioridade] primeira decisão = %s -> %s\n",
               o.primeira_decisao == 1 ? "renas" : (o.primeira_decisao == 2 ? "elfos" : "nenhuma"),
               ok1 ? "OK" : "FALHOU");
        printf("[teste-prioridade] elfos atendidos = %d/%d -> %s\n", m.concluidos, m.previstos,
               ok2 ? "OK" : "FALHOU");
        printf("[teste-prioridade] violações (prioridade=%d, regras=%d) -> %s\n",
               m.violacoes_prioridade, m.violacoes_regras, ok3 ? "OK" : "FALHOU");
        int passou = ok1 && ok2 && ok3 && ok4;
        printf("[teste-prioridade] RESULTADO: %s\n", passou ? "PASSOU" : "FALHOU");
        rc = passou ? 0 : 1;
    } else if (strcmp(m.status, "ok") != 0) {
        rc = 2;
    }
    if (erro_csv)
        rc = 1;

    liberar_oficina(&o);
    free(th_elfos);
    free(arg_elfos);
    return rc;
}
