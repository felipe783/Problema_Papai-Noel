#ifndef RELOGIO_H
#define RELOGIO_H

#include "comum.h"

void relogio_iniciar(Relogio *r, double velocidade);
double relogio_agora(Relogio *r);            /* ms virtuais desde o início */
void relogio_pausar(Relogio *r, int pausar);
void relogio_velocidade(Relogio *r, double v);
void relogio_encerrar(Relogio *r);
void relogio_estado(Relogio *r, int *pausado, double *velocidade);

/* Dorme `ms` virtuais. Não avança durante a pausa e retorna cedo no
 * encerramento. Serve SOMENTE para simular durações. */
void relogio_dormir(Relogio *r, double ms);

#endif
