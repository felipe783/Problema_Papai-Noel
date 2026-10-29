/*
 * saida.c — eventos em JSON Lines (para o servidor/interface) ou texto.
 *
 * Cada linha carrega o evento E o estado inteiro, então a interface nunca
 * precisa reconstruir o estado somando eventos: basta desenhar a última
 * linha recebida. Um cliente que conecta no meio da execução se sincroniza
 * com uma única linha.
 */
#include "comum.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "relogio.h"
#include "saida.h"

static const char *NOME_NOEL[] = { "dormindo", "ajudando", "preparando", "viajando", "encerrado" };
static const char COD_RENA[] = { 'F', 'E', 'A', 'V' };
static const char COD_ELFO[] = { 'T', 'E', 'F', 'A' };

typedef struct {
    char *p;
    size_t n, cap;
} Buf;

static void put(Buf *b, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
static void put(Buf *b, const char *fmt, ...)
{
    if (b->n >= b->cap)
        return;
    va_list ap;
    va_start(ap, fmt);
    int k = vsnprintf(b->p + b->n, b->cap - b->n, fmt, ap);
    va_end(ap);
    if (k > 0)
        b->n += (size_t)k;
}

static void put_grupo(Buf *b, const Grupo *g)
{
    put(b, "{\"id\":%d,\"m\":[", g->id);
    for (int k = 0; k < g->n; k++)
        put(b, "%s%d", k ? "," : "", g->membros[k]);
    put(b, "]}");
}

static double media(double soma, long n) { return n ? soma / (double)n : 0.0; }

void emitir(Oficina *o, const char *quem, int id, const char *ev, int grupo,
            const char *fmt, ...)
{
    char msg[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);

    double t = relogio_agora(o->rel);
    o->seq++;

    if (o->cfg->texto) {
        printf("[%9.1f s] %-5s %s\n", t / 1000.0, quem, msg);
        fflush(stdout);
        return;
    }

    char mem[16384];
    Buf b = { mem, 0, sizeof mem };
    int pausado;
    double vel;
    relogio_estado(o->rel, &pausado, &vel);

    put(&b, "{\"seq\":%ld,\"t\":%.1f,\"quem\":\"%s\",\"id\":%d,\"ev\":\"%s\",\"grupo\":%d,\"msg\":\"%s\",",
        o->seq, t, quem, id, ev, grupo, msg);

    put(&b, "\"noel\":\"%s\",\"renas\":\"", NOME_NOEL[o->noel]);
    for (int i = 0; i < NUM_RENAS; i++)
        put(&b, "%c", COD_RENA[o->rena[i]]);
    put(&b, "\",\"elfos\":\"");
    for (int i = 0; i < o->cfg->elfos; i++)
        put(&b, "%c", COD_ELFO[o->elfo[i]]);
    put(&b, "\",\"grupo_do_elfo\":[");
    for (int i = 0; i < o->cfg->elfos; i++)
        put(&b, "%s%d", i ? "," : "", o->grupo_do_elfo[i]);

    put(&b, "],\"aberto\":");
    put_grupo(&b, GRUPO(o, o->grupo_aberto));
    put(&b, ",\"fila\":[");
    for (int g = o->proximo_grupo; g < o->grupo_aberto; g++) {
        if (g > o->proximo_grupo)
            put(&b, ",");
        put_grupo(&b, GRUPO(o, g));
    }
    put(&b, "],\"em_ajuda\":");
    if (o->grupo_em_ajuda)
        put_grupo(&b, GRUPO(o, o->grupo_em_ajuda));
    else
        put(&b, "null");

    put(&b, ",\"m\":{\"viagens\":%d,\"grupos\":%ld,\"pedidos\":%ld,\"disputas\":%ld,\"violacoes\":%ld,"
            "\"esp_med\":%.1f,\"esp_max\":%.1f,\"resp_med\":%.1f,\"resp_max\":%.1f,\"util\":%.3f,\"esperas\":[",
        o->viagens_concluidas, o->grupos_atendidos, o->pedidos, o->disputas, o->violacoes,
        media(o->espera_soma, o->espera_n), o->espera_max,
        media(o->resposta_soma, o->viagens_concluidas), o->resposta_max,
        t > 0 ? o->ocupado_ms / t : 0.0);
    if (strcmp(ev, "inicio_ajuda") == 0)
        for (int k = 0; k < o->n_ultimas; k++)
            put(&b, "%s%.1f", k ? "," : "", o->ultimas_esperas[k]);
    put(&b, "]},\"ctl\":{\"pausado\":%s,\"vel\":%.3g,\"elfos\":%d}}\n",
        pausado ? "true" : "false", vel, o->cfg->elfos);

    fputs(mem, stdout);
    fflush(stdout);
}

void imprimir_resumo(Oficina *o)
{
    double t = relogio_agora(o->rel);
    fprintf(stderr,
            "\n== Resumo (%.1f s virtuais) ==\n"
            "viagens: %d | grupos atendidos: %ld | pedidos de elfos: %ld\n"
            "espera dos elfos: média %.0f ms, máx %.0f ms\n"
            "resposta às renas: média %.0f ms, máx %.0f ms\n"
            "decisões com disputa (renas venceram): %ld | utilização do Noel: %.0f%%\n"
            "violações de invariantes: %ld\n",
            t / 1000.0, o->viagens_concluidas, o->grupos_atendidos, o->pedidos,
            media(o->espera_soma, o->espera_n), o->espera_max,
            media(o->resposta_soma, o->viagens_concluidas), o->resposta_max,
            o->disputas, t > 0 ? 100.0 * o->ocupado_ms / t : 0.0, o->violacoes);
}
