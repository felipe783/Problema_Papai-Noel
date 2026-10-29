/* csv.h — exportação dos resultados (só depois dos joins). */
#ifndef CSV_H
#define CSV_H

#include "comum.h"
#include "metricas.h"

/* Identificadores da execução, gravados em todas as linhas. */
typedef struct {
    char execucao[96];    /* ex.: E06_R10_rep1 */
    char configuracao[32];/* ex.: E06_R10 */
    const char *conjunto; /* referencia | 1 | 2 | teste | ingenua | fora */
} IdExecucao;

void montar_id(const Config *c, IdExecucao *id);

/* Acrescenta uma linha em resumo.csv e as linhas de eventos.csv e
 * espera_elfos.csv em cfg->out. Cria o cabeçalho se o arquivo não existir.
 * Retorna 0 em sucesso. */
int exportar_csv(const Oficina *o, const Metricas *m, const IdExecucao *id);

#endif
