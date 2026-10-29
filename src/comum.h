/*
 * comum.h — tipos e estado compartilhado do Problema do Papai Noel, versão
 * INFINITA (Noel, renas e elfos repetem seus ciclos até o encerramento).
 *
 * Todo arquivo .c inclui este cabeçalho PRIMEIRO, para que _POSIX_C_SOURCE
 * valha antes de qualquer cabeçalho do sistema.
 */
#ifndef COMUM_H
#define COMUM_H

#define _POSIX_C_SOURCE 200809L

#include <pthread.h>
#include <time.h>

#define NUM_RENAS 9   /* renas necessárias para a viagem */
#define TAM_GRUPO 3   /* elfos por atendimento */
#define MIN_ELFOS 3
#define MAX_ELFOS 60  /* limite para a interface continuar legível */
#define CAP_GRUPOS 32 /* anel de grupos: > MAX_ELFOS/3 + 1 grupos vivos */

typedef enum {
    NOEL_DORMINDO = 0,
    NOEL_AJUDANDO,
    NOEL_PREPARANDO, /* atrelando as renas ao trenó */
    NOEL_VIAJANDO,   /* entregando presentes: não atende elfos */
    NOEL_ENCERRADO
} EstadoNoel;

typedef enum { RENA_FERIAS = 0, RENA_ESTABULO, RENA_ATRELADA, RENA_VIAJANDO } EstadoRena;

typedef enum {
    ELFO_TRABALHANDO = 0,
    ELFO_ESPERANDO,     /* no grupo aberto, aguardando completar 3 */
    ELFO_NA_FILA,       /* grupo fechado, aguardando Noel */
    ELFO_SENDO_AJUDADO
} EstadoElfo;

/* Parâmetros (linha de comando). Durações em ms de tempo VIRTUAL. */
typedef struct {
    int elfos;
    int ferias_min, ferias_max;     /* férias de cada rena */
    int trabalho_min, trabalho_max; /* trabalho do elfo até precisar de ajuda */
    int ajuda_ms, preparo_ms, viagem_ms;
    unsigned semente;
    double velocidade;   /* ms virtuais por ms real */
    double duracao_s;    /* 0 = infinito */
    int texto;           /* saída legível em vez de JSON */
} Config;

/*
 * Relógio virtual: permite pausar e acelerar a simulação sem que as
 * threads percam a noção de tempo. Protegido pelo seu próprio mutex.
 * Ordem de locks: Oficina.mutex -> Relogio.m (nunca o contrário).
 */
typedef struct {
    pthread_mutex_t m;
    pthread_cond_t cv;      /* acorda quem dorme durante a pausa */
    int pausado, encerrar;
    double velocidade;
    struct timespec real_base;
    double virt_base;       /* ms virtuais em real_base */
} Relogio;

typedef struct {
    int id;                  /* 1, 2, ... (crescente para sempre) */
    int membros[TAM_GRUPO];
    int n;
    double t_pronto;
} Grupo;

/* Estado compartilhado. Todos os campos são protegidos por `mutex`. */
typedef struct {
    const Config *cfg;
    Relogio *rel;

    pthread_mutex_t mutex;
    pthread_cond_t cv_noel;  /* Noel dorme aqui */
    pthread_cond_t cv_elfos; /* elfos esperam o fim da ajuda do seu grupo */
    pthread_cond_t cv_renas; /* renas esperam o fim da viagem */
    int encerrar;

    /* Noel */
    EstadoNoel noel;
    int grupo_em_ajuda;      /* id do grupo sendo ajudado; 0 = nenhum */
    double ocupado_ms;

    /* renas */
    EstadoRena *rena;
    int renas_estabulo;      /* renas que voltaram e esperam a próxima viagem */
    int viagens_concluidas;
    double t_nona;

    /* elfos: fila de grupos num anel indexado por id % CAP_GRUPOS */
    EstadoElfo *elfo;
    int *grupo_do_elfo;      /* 0 = trabalhando */
    double *t_pedido;
    Grupo grupos[CAP_GRUPOS];
    int grupo_aberto;        /* id do grupo que aceita novos elfos */
    int proximo_grupo;       /* próximo id a ser atendido (FIFO) */
    int ultimo_concluido;    /* maior id já atendido */

    /* métricas */
    long pedidos, grupos_atendidos, disputas;
    double espera_soma, espera_max; long espera_n;
    double resposta_soma, resposta_max;
    double ultimas_esperas[TAM_GRUPO]; int n_ultimas;

    /* invariantes (devem ficar sempre em zero) */
    long violacoes;

    long seq;                /* número do evento emitido */
} Oficina;

#define GRUPO(o, id) (&(o)->grupos[(id) % CAP_GRUPOS])

#endif
