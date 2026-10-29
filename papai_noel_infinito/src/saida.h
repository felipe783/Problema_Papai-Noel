#ifndef SAIDA_H
#define SAIDA_H

#include "comum.h"

/*
 * Emite um evento em stdout: uma linha JSON com o evento e o retrato
 * completo do estado (ou uma linha legível, com --texto).
 * Deve ser chamada com o->mutex adquirido: o retrato é consistente.
 */
void emitir(Oficina *o, const char *quem, int id, const char *ev, int grupo,
            const char *fmt, ...) __attribute__((format(printf, 6, 7)));

/* Resumo final em stderr. Chamada depois dos joins. */
void imprimir_resumo(Oficina *o);

#endif
