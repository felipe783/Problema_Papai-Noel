/* metricas.h — métricas e invariantes calculados depois dos joins. */
#ifndef METRICAS_H
#define METRICAS_H

#include "comum.h"

typedef struct {
    double T_ms;           /* sinal de início -> encerramento de Noel */
    int previstos;         /* pedidos de elfos previstos (= elfos) */
    int concluidos;        /* pedidos de elfos atendidos */
    double vazao;          /* concluidos / (T_ms / 1000) */
    int n_amostras;        /* esperas medidas */
    double espera_media, espera_p95, espera_max; /* ms; < 0 = N/A */
    double resposta_renas; /* ms; < 0 = N/A */
    double utilizacao;     /* fração de T com Noel ocupado */
    int violacoes_prioridade, violacoes_regras;
    const char *status;    /* ok | timeout | violacao */
} Metricas;

/* p95 de n valores: ordena e pega a posição ceil(0,95·n) (base 1).
 * Retorna -1 se n == 0. Ordena o vetor no lugar. */
double percentil95(double *v, int n);

/* Fecha os invariantes finais (atendido 0 ou 2+ vezes, viagem não feita)
 * e calcula as métricas. */
void calcular_metricas(Oficina *o, Metricas *m);

#endif
