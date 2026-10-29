/*
 * metricas.c — cálculo das métricas e verificação final dos invariantes.
 * Roda depois de todos os pthread_join; não há concorrência aqui.
 */
#include "comum.h"

#include <stdlib.h>

#include "metricas.h"

static int cmp_double(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

double percentil95(double *v, int n)
{
    if (n <= 0)
        return -1.0;
    qsort(v, (size_t)n, sizeof(double), cmp_double);
    /* ceil(0,95·n) em inteiros: (95n + 99) / 100, base 1 */
    int pos = (95 * n + 99) / 100;
    if (pos < 1)
        pos = 1;
    return v[pos - 1];
}

void calcular_metricas(Oficina *o, Metricas *m)
{
    const Config *c = o->cfg;

    /* Invariantes finais, só quando o episódio terminou normalmente:
     * num timeout os pedidos pendentes já estão explicados pelo status. */
    if (!o->abortar) {
        for (int e = 0; e < c->elfos; e++)
            if (o->atendimentos[e] != 1)
                o->violacoes_regras++; /* atendido nunca ou duas vezes */
        if (!o->viagem_concluida)
            o->violacoes_regras++;
    }

    m->T_ms = o->t_encerramento;
    m->previstos = c->elfos;
    m->concluidos = 0;
    for (int e = 0; e < c->elfos; e++)
        if (o->atendimentos[e] >= 1)
            m->concluidos++;
    m->vazao = m->T_ms > 0 ? m->concluidos / (m->T_ms / 1000.0) : 0.0;

    /* Esperas: só de quem teve a ajuda iniciada. */
    double *esp = malloc(sizeof(double) * (size_t)(c->elfos > 0 ? c->elfos : 1));
    int n = 0;
    double soma = 0.0, max = -1.0;
    for (int e = 0; e < c->elfos; e++) {
        if (o->t_inicio_ajuda[e] < 0 || o->t_pedido[e] < 0)
            continue;
        double w = o->t_inicio_ajuda[e] - o->t_pedido[e];
        esp[n++] = w;
        soma += w;
        if (w > max)
            max = w;
    }
    m->n_amostras = n;
    m->espera_media = n ? soma / n : -1.0;
    m->espera_max = n ? max : -1.0;
    m->espera_p95 = percentil95(esp, n);
    free(esp);

    m->resposta_renas = o->viagem_iniciada ? o->t_ini_preparo - o->t_nona : -1.0;
    m->utilizacao = m->T_ms > 0 ? o->ocupado_ms / m->T_ms : 0.0;
    m->violacoes_prioridade = o->violacoes_prioridade;
    m->violacoes_regras = o->violacoes_regras;

    if (o->abortar)
        m->status = "timeout";
    else if (m->violacoes_prioridade > 0 || m->violacoes_regras > 0 || o->eventos_perdidos > 0)
        m->status = "violacao";
    else
        m->status = "ok";
}
