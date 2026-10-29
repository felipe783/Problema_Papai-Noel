/*
 * comum.h — tipos e estado compartilhado do Problema do Papai Noel (Tema 11).
 *
 * Todo arquivo .c inclui este cabeçalho PRIMEIRO, para que _POSIX_C_SOURCE
 * valha antes de qualquer cabeçalho do sistema (clock_nanosleep,
 * pthread_condattr_setclock e CLOCK_MONOTONIC dependem dele).
 */
#ifndef COMUM_H
#define COMUM_H

#define _POSIX_C_SOURCE 200809L

#include <pthread.h>
#include <time.h>

#define NUM_RENAS 9   /* renas necessárias para a viagem */
#define TAM_GRUPO 3   /* elfos por atendimento */
#define MAX_ELFOS 300 /* limite de segurança para --elfos */

/* Estado de Noel, gravado em cada evento. */
typedef enum {
    NOEL_DORMINDO = 0,
    NOEL_AJUDANDO,
    NOEL_PREPARANDO,
    NOEL_ENCERRADO
} EstadoNoel;

typedef enum { PART_NOEL = 0, PART_ELFO, PART_RENA } TipoParticipante;

typedef enum {
    EV_CHEGADA = 0,
    EV_GRUPO_PRONTO,
    EV_NONA_RENA,
    EV_DECISAO,
    EV_INICIO_AJUDA,
    EV_FIM_AJUDA,
    EV_INICIO_PREPARACAO,
    EV_FIM_PREPARACAO,
    EV_ENCERRAMENTO,
    EV_TIMEOUT
} TipoEvento;

/* Um evento da linha do tempo; t_ms é relativo ao sinal de início. */
typedef struct {
    double t_ms;
    int participante;      /* id do elfo/rena; 0 para Noel */
    TipoParticipante tipo;
    TipoEvento evento;
    EstadoNoel estado_noel; /* estado de Noel logo após o evento */
    int grupo_id;           /* 1, 2, ...; 0 = sem grupo (viagem ou nenhum) */
} Evento;

/* Parâmetros da execução (linha de comando). */
typedef struct {
    int elfos;           /* quantidade de elfos (múltiplo de 3) */
    int renas_ms;        /* instante de chegada das 9 renas */
    int rep;             /* número da repetição (1..5) */
    int semente;         /* id registrado da repetição (sem aleatoriedade) */
    const char *out;     /* pasta de saída dos CSVs */
    int teste_prioridade;/* Noel só é liberado com renas E grupo prontos */
    int ingenua;         /* política ingênua: elfos antes das renas */
    int timeout_ms;      /* timeout de segurança do episódio */
    int elfo0_ms;        /* chegada do elfo 0 (elfo i chega em elfo0_ms + i) */
    int ajuda_ms;        /* duração de uma ajuda */
    int preparo_ms;      /* duração da preparação da viagem */
} Config;

/* Estados de um grupo de elfos. */
typedef enum { GRUPO_ABERTO = 0, GRUPO_PRONTO, GRUPO_EM_AJUDA, GRUPO_CONCLUIDO } EstadoGrupo;

typedef struct {
    int membros[TAM_GRUPO];
    int n;               /* membros já inscritos */
    EstadoGrupo estado;
    double t_pronto, t_inicio, t_fim;
} Grupo;

/* Estado compartilhado. Todos os campos são protegidos por `mutex`. */
typedef struct {
    const Config *cfg;

    pthread_mutex_t mutex;
    pthread_cond_t cv_largada; /* sinal de início comum */
    pthread_cond_t cv_noel;    /* Noel dorme aqui (relógio monotônico) */
    pthread_cond_t cv_elfos;   /* elfos esperam o fim da ajuda do seu grupo */
    pthread_cond_t cv_renas;   /* renas esperam o fim da preparação */

    /* largada */
    int total_threads, threads_prontas, largada;
    struct timespec t0;

    /* elfos e grupos */
    Grupo *grupos;
    int n_grupos;          /* elfos / 3 */
    int grupo_aberto;      /* índice do grupo que aceita novos elfos */
    int grupos_fechados;   /* grupos com 3 membros (prontos ou além) */
    int proximo_grupo;     /* próximo grupo da fila a ser atendido */
    int grupos_concluidos;
    double *t_pedido, *t_inicio_ajuda;
    int *grupo_do_elfo, *atendimentos;

    /* renas */
    int renas_prontas;
    double t_nona;
    int viagem_iniciada, viagem_concluida;
    double t_ini_preparo, t_fim_preparo;

    /* Noel */
    EstadoNoel estado;
    int noel_liberado;     /* usado só em --teste-prioridade */
    int ajuda_em_curso;    /* para detectar ajuda interrompida */
    double ocupado_ms;     /* tempo em ajuda ou preparação */
    double t_encerramento;
    int abortar;           /* timeout: todos saem */
    int decisoes, decisoes_com_disputa, primeira_decisao; /* 1 renas, 2 elfos */

    /* invariantes */
    int violacoes_prioridade, violacoes_regras;

    /* eventos em memória, exportados só depois dos joins */
    Evento *eventos;
    int n_eventos, cap_eventos, eventos_perdidos;
} Oficina;

/* Espera o sinal de início. Deve ser chamada com o mutex adquirido. */
void esperar_largada(Oficina *o);

/* Registra um evento. Deve ser chamada com o mutex adquirido. */
void registrar(Oficina *o, TipoParticipante tipo, int participante,
               TipoEvento ev, int grupo_id);

#endif
