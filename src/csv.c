/*
 * csv.c — gravação de resumo.csv, eventos.csv e espera_elfos.csv.
 * Os arquivos são abertos em modo de acréscimo, então várias execuções
 * se acumulam na mesma pasta; o cabeçalho só é escrito no arquivo novo.
 */
#include "comum.h"

#include <stdio.h>
#include <string.h>

#include "csv.h"

static const char *NOME_EVENTO[] = {
    "chegada", "grupo_pronto", "nona_rena", "decisao", "inicio_ajuda",
    "fim_ajuda", "inicio_preparacao", "fim_preparacao", "encerramento", "timeout"};
static const char *NOME_TIPO[] = {"noel", "elfo", "rena"};
static const char *NOME_ESTADO[] = {"dormindo", "ajudando", "preparando", "encerrado"};

void montar_id(const Config *c, IdExecucao *id)
{
    snprintf(id->configuracao, sizeof id->configuracao, "E%02d_R%02d", c->elfos, c->renas_ms);
    if (c->teste_prioridade && c->ingenua)
        id->conjunto = "teste_ingenua";
    else if (c->teste_prioridade)
        id->conjunto = "teste";
    else if (c->ingenua)
        id->conjunto = "ingenua";
    else if (c->elfos == 6 && c->renas_ms == 10)
        id->conjunto = "referencia";
    else if (c->renas_ms == 10)
        id->conjunto = "1";
    else if (c->elfos == 6)
        id->conjunto = "2";
    else
        id->conjunto = "fora";

    const char *pref = c->teste_prioridade ? "teste_" : (c->ingenua ? "ingenua_" : "");
    snprintf(id->execucao, sizeof id->execucao, "%s%s%s_rep%d",
             pref, c->teste_prioridade && c->ingenua ? "ingenua_" : "", id->configuracao, c->rep);
}

/* Abre <dir>/<nome> para acréscimo; *novo = 1 se o arquivo estava vazio. */
static FILE *abrir(const char *dir, const char *nome, int *novo)
{
    char caminho[1024];
    size_t n = strlen(dir);
    snprintf(caminho, sizeof caminho, "%s%s%s", dir, (n && dir[n - 1] == '/') ? "" : "/", nome);
    FILE *f = fopen(caminho, "a");
    if (!f) {
        perror(caminho);
        return NULL;
    }
    fseek(f, 0, SEEK_END);
    *novo = ftell(f) == 0;
    return f;
}

/* Valor em ms com 3 casas, ou N/A se negativo (sem amostra). */
static void campo_ms(FILE *f, double v)
{
    if (v < 0)
        fprintf(f, ",N/A");
    else
        fprintf(f, ",%.3f", v);
}

int exportar_csv(const Oficina *o, const Metricas *m, const IdExecucao *id)
{
    const Config *c = o->cfg;
    int novo;

    FILE *f = abrir(c->out, "resumo.csv", &novo);
    if (!f)
        return -1;
    if (novo)
        fprintf(f, "tema,configuracao,conjunto,repeticao,semente,elfos,renas_ms,T_ms,"
                   "previstos,concluidos,vazao_pedidos_s,espera_media_ms,espera_p95_ms,"
                   "espera_max_ms,n_amostras,resposta_renas_ms,violacoes_prioridade,"
                   "violacoes_regras,utilizacao_noel,status\n");
    fprintf(f, "11_papai_noel,%s,%s,%d,%d,%d,%d,%.3f,%d,%d,%.2f",
            id->configuracao, id->conjunto, c->rep, c->semente, c->elfos, c->renas_ms,
            m->T_ms, m->previstos, m->concluidos, m->vazao);
    campo_ms(f, m->espera_media);
    campo_ms(f, m->espera_p95);
    campo_ms(f, m->espera_max);
    fprintf(f, ",%d", m->n_amostras);
    campo_ms(f, m->resposta_renas);
    fprintf(f, ",%d,%d,%.4f,%s\n", m->violacoes_prioridade, m->violacoes_regras,
            m->utilizacao, m->status);
    fclose(f);

    f = abrir(c->out, "eventos.csv", &novo);
    if (!f)
        return -1;
    if (novo)
        fprintf(f, "execucao,t_ms,participante,tipo,evento,estado_noel,grupo_id\n");
    for (int i = 0; i < o->n_eventos; i++) {
        const Evento *e = &o->eventos[i];
        fprintf(f, "%s,%.3f,%d,%s,%s,%s,", id->execucao, e->t_ms, e->participante,
                NOME_TIPO[e->tipo], NOME_EVENTO[e->evento], NOME_ESTADO[e->estado_noel]);
        if (e->grupo_id > 0)
            fprintf(f, "%d", e->grupo_id);
        fputc('\n', f);
    }
    fclose(f);

    f = abrir(c->out, "espera_elfos.csv", &novo);
    if (!f)
        return -1;
    if (novo)
        fprintf(f, "execucao,elfo_id,grupo_id,t_pedido_ms,t_inicio_ajuda_ms,espera_ms\n");
    for (int e = 0; e < c->elfos; e++) {
        fprintf(f, "%s,%d,", id->execucao, e);
        if (o->grupo_do_elfo[e] >= 0)
            fprintf(f, "%d", o->grupo_do_elfo[e] + 1);
        else
            fprintf(f, "N/A");
        campo_ms(f, o->t_pedido[e]);
        campo_ms(f, o->t_inicio_ajuda[e]);
        if (o->t_pedido[e] >= 0 && o->t_inicio_ajuda[e] >= 0)
            campo_ms(f, o->t_inicio_ajuda[e] - o->t_pedido[e]);
        else
            fprintf(f, ",N/A");
        fputc('\n', f);
    }
    fclose(f);
    return 0;
}
