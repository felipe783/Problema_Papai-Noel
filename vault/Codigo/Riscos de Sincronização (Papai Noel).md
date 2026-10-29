# Riscos de Sincronização (Papai Noel)

Análise de cada erro clássico de sincronização frente ao código real. Cada risco tem uma classificação:

- **[ERRO NO CÓDIGO]**: defeito que existe no código atual, mesmo que não se manifeste nos experimentos.
- **[RISCO TEÓRICO]**: só aconteceria com outra ordem de execução, outra entrada ou uma mudança no código.
- **[DESCARTADO]**: a análise mostra que não pode acontecer com o código atual.

Os mecanismos citados estão explicados em [[Sincronização no Código (Papai Noel)]]. Índice: [[_Papai-Noel]].

> **Limite das garantias.** A ausência de corridas foi verificada **por inspeção do código**, pelas invariantes contadas em tempo de execução, por 25 + 300 execuções sem falha e pelo teste de prioridade. **Não** foi verificada por ferramenta: ThreadSanitizer e Helgrind não estão instalados nesta máquina (2026-10-28). Testes mostram a presença de erros, não a ausência.

## Resumo

| Risco | Classificação | Onde olhar |
|---|---|---|
| Condição de corrida | [DESCARTADO] por inspeção; não verificado por ferramenta | todo acesso mutável está entre lock e unlock |
| Entrada indevida em seção crítica | [DESCARTADO] | todo `lock` tem `unlock` em cada caminho |
| Perda de notificação | o `signal` de `cv_noel` pode "se perder", mas o efeito está [DESCARTADO] | `noel.c:89-90` reavalia antes de dormir |
| Espera que nunca termina | [RISCO TEÓRICO] em dois pontos sem prazo | `main.c:208`, `noel.c:107` |
| Deadlock | [DESCARTADO] | um único mutex, não recursivo, sem lock aninhado |
| Starvation / espera excessiva | [DESCARTADO] na versão finita; [RISCO TEÓRICO] numa versão contínua | `noel.c:117` |
| Violação de prioridade | [DESCARTADO] no modo normal; demonstrada no `--ingenua` | `noel.c:117-119` |
| Grupo com quantidade errada | [DESCARTADO] | `elfo.c:34-54` |
| Viagem antes das 9 renas | [DESCARTADO] | `noel.c:89` |
| Encerramento prematuro / thread que não termina | [DESCARTADO] | `noel.c:86-87`, `135-145`, `main.c:215-219` |
| Retornos de init não verificados | **[ERRO NO CÓDIGO]** (robustez) | `main.c:131-139` |
| Caminho de erro do `pthread_create` sem join | **[ERRO NO CÓDIGO]** (robustez) | `main.c:187-204` |
| Checagens de invariante que nunca disparam | **[ERRO NO CÓDIGO]** (limitação de medição) | `noel.c:111`, `noel.c:48`, `noel.c:21`, `elfo.c:36` |

## 1. Condição de corrida

- **Causa possível:** uma thread ler ou escrever estado compartilhado sem o mutex.
- **Análise:** toda escrita em campos mutáveis da `Oficina` acontece com o mutex (tabela em [[Sincronização no Código (Papai Noel)#2.4 Que dados ele protege]]). Há leituras **sem lock** apenas de `o->cfg` (por exemplo `elfo.c:25`, `noel.c:79`) e de `o->t0` (`dormir_ate_ms`, `tempo.c:45`). `cfg` é preenchido antes do `pthread_create`, que estabelece *happens-before* com a nova thread. `t0` é gravado pela main **com o mutex** (`main.c:210`) antes de `largada = 1`, e cada thread só o lê depois de ver `largada == 1` com o mesmo mutex. Depois disso, nenhum dos dois muda.
- **Consequência, se existisse:** contadores com atualização perdida (veja o exemplo de `renas_prontas` em [[Sincronização no Código (Papai Noel)#2.7 O que daria errado sem o mutex ou com uso incorreto]]).
- **Como detectar ou evitar:** compilar com `-fsanitize=thread` ou rodar com `valgrind --tool=helgrind`, que não estão disponíveis aqui; manter a regra "todo estado mutável só com o mutex".

## 2. Entrada indevida numa seção crítica

- **Análise:** existe um único mutex, e todo caminho que o trava o libera. No elfo há três saídas, `elfo.c:29`, `38` e `59`, todas com unlock. Na rena, `rena.c:25` e `38`. No Noel, `noel.c:145` no fim, mais o par `unlock/lock` em torno de cada sleep (`noel.c:31/33`, `60/62`).
- **Ponto de atenção:** enquanto Noel dorme na ajuda **sem o mutex**, elfos e renas entram em suas seções críticas e alteram `grupos_fechados`, `renas_prontas` e `grupos[k]`. Isso é intencional. Noel não confia no que leu antes de dormir: quando volta (`noel.c:62`), só mexe no grupo `g`, que nenhuma outra thread altera enquanto ele está `EM_AJUDA`, e depois reavalia tudo no topo do laço.

## 3. Perda de notificação

- **O que é:** um `signal` enviado quando ninguém está esperando se perde, porque cond vars não têm memória.
- **Onde acontece:** em `elfo.c:53` e `rena.c:33`, quando Noel está ajudando ou preparando (fora de `cv_noel`).
- **Por que não causa erro:** o **estado** fica gravado (`grupos_fechados++`, `renas_prontas == 9`), e Noel **testa o predicado antes de dormir** (`noel.c:89-100`). O aviso só é necessário se Noel já estiver dormindo, e, nesse caso, ele está na fila e recebe o aviso.
- **A janela clássica "testei, mas ainda não dormi" não existe:** o teste e a espera acontecem com o mutex, e `pthread_cond_timedwait` solta o mutex e dorme atomicamente. Uma rena não consegue mudar o estado entre o teste de Noel e o início do sono.
- **Onde seria um erro de verdade:** trocar o `broadcast` de `main.c:28` por `signal` (o aviso pode acordar a thread errada, e a main nunca acorda; ver [[Sincronização no Código (Papai Noel)]], seção 4.1). Também seria erro se alguém sinalizasse **antes** de gravar o estado ou fora do mutex.

## 4. Esperas que nunca terminam

| Ponto | Situação | Classificação |
|---|---|---|
| `main.c:208-209` | a main espera todas as threads se anunciarem, **sem prazo**. Se uma thread morresse antes de `esperar_largada`, a main ficaria esperando para sempre. | [RISCO TEÓRICO]: não acontece com o código atual |
| `noel.c:101-107` | se `pthread_cond_timedwait` devolvesse um erro diferente de `ETIMEDOUT` (como `EINVAL` para prazo inválido), o `continue` repetiria a chamada sem dormir. Isso seria **espera ocupada** sem fim, e o timeout nunca seria reconhecido. | [RISCO TEÓRICO]: `limite` é sempre válido |
| `elfo.c:57`, `rena.c:36` | só terminam se Noel concluir ou abortar. Noel sempre faz broadcast nos dois casos (`noel.c:73`, `41`, `143-144`). | [DESCARTADO] |
| Mutex nunca liberado | trava tudo, até o timeout (2.7 da nota de sincronização) | [DESCARTADO] no código atual |

## 5. Deadlock

As quatro condições de Coffman precisam valer **juntas**: exclusão mútua, posse e espera, não preempção e **espera circular**.

- Há **um único** mutex, então nenhuma thread segura um recurso enquanto espera outro **lock**, e não pode haver espera circular entre locks.
- O mutex **não é travado duas vezes** pela mesma thread: `preparar_viagem`/`ajudar_grupo` recebem o mutex já travado (`noel.c:18`, `44`).
- Esperar numa cond var **solta** o mutex, então quem espera não segura nada.
- Cada predicado de espera tem **quem o torne verdadeiro** e **quem avise** (tabelas da seção 4 da nota de sincronização). Isso elimina o "deadlock de lógica" em que todos esperam por um aviso que ninguém dará.
- **Classificação:** [DESCARTADO]. Evidência prática: 25 + 300 execuções sem nenhum timeout [CONFIRMADO 2026-10-28].

## 6. Starvation e espera excessiva

- **Versão finita, entre tipos:** existe no máximo **uma** viagem de 5 ms, então os elfos esperam por ela uma única vez. [DESCARTADO]
- **Entre elfos:** os grupos são atendidos em **FIFO** (`proximo_grupo++`, `noel.c:128`), e o grupo `k` fecha antes do `k+1` porque `grupo_aberto` só cresce (`elfo.c:50-51`). A espera de um grupo na posição *k* da fila é limitada por ≈ 5 + 3(*k* − 1) ms mais o tempo de formação. [DESCARTADO]
- **Fila do mutex:** a POSIX não garante FIFO no `pthread_mutex_lock`. Na teoria, uma thread poderia perder a disputa várias vezes seguidas, mas com no máximo 22 threads e seções críticas de microssegundos isso é irrelevante. [RISCO TEÓRICO]
- **Versão contínua (fora do escopo):** se as renas voltassem sempre, `escolhe_renas = renas_ok` (`noel.c:117`) poderia deixar grupos de elfos esperando indefinidamente. Mitigações possíveis: *aging* (um grupo que espera mais que X ganha prioridade), uma cota (pelo menos um grupo entre duas viagens) ou um limite de viagens consecutivas. [RISCO TEÓRICO]
- **Espera excessiva medida:** com as renas junto, o p95 da espera sobe de ~2,1 ms para ~5,2 ms. Esse é o custo esperado da prioridade, não um defeito ([[Testes e Gráficos (Papai Noel)]]).

### 6.1 Versão contínua: o que mudaria (hipotético)

**O projeto implementa só a versão finita.** O esboço abaixo **não foi escrito nem testado**; serve para responder "e se fosse contínuo?". Na versão contínua, todo mundo repete o ciclo para sempre:
- as renas: férias → chegada → viagem → entrega → férias;
- os elfos: trabalho → pedido → ajuda → trabalho;
- o Noel: nunca termina.

A estrutura de sincronização é a mesma (1 mutex, variáveis de condição, espera em `while`). O que muda são **os predicados**, e aparecem três problemas novos:

| Problema novo | Por que aparece | Solução |
|---|---|---|
| **Reaproveitar o estado** | hoje a rena espera `while (!viagem_concluida)`, uma flag que vira 1 **uma vez**. Se o Noel a zerasse para a próxima viagem, uma rena acordada pelo `broadcast` mas ainda na fila do mutex poderia testar a flag já zerada e **voltar a dormir**, presa numa viagem que já passou | **contador de gerações**: `viagens_feitas` só cresce; cada rena guarda `minha = viagens_feitas` e espera `while (viagens_feitas == minha)`. Para os elfos: ids de grupo que só crescem, esperando `while (grupos_concluidos <= g)` (vale porque o atendimento é FIFO) |
| **Starvation dos elfos** | se as renas voltam rápido, podem estar **sempre** prontas quando o Noel termina; com `escolhe_renas = renas_ok` (`noel.c:117`), os elfos nunca seriam atendidos | **aging** (um grupo que espera mais que X ms vence as renas) ou **cota** (no máximo K viagens seguidas). Troca prioridade absoluta por justiça |
| **Encerrar** | `viagem_concluida && grupos_concluidos == n_grupos` (`noel.c:86`) nunca acontece | flag `encerrar` ligada pela `main`, `broadcast` em **todas** as variáveis de condição e `&& !encerrar` em todo `while` (o código já faz algo parecido com `abortar`, `noel.c:142-144`) |

Esboço (pseudocódigo, não compilado):

```c
// rena
for (;;) {
    dormir(ferias_ms);
    lock(&mutex);
    int minha = viagens_feitas;
    if (++renas_prontas == 9) signal(&cv_noel);
    while (viagens_feitas == minha && !encerrar) wait(&cv_renas, &mutex);
    unlock(&mutex);
    dormir(entrega_ms);
}

// elfo
for (;;) {
    dormir(trabalho_ms);
    lock(&mutex);
    long g = grupo_aberto;
    if (++n_no_grupo == 3) { grupo_aberto++; n_no_grupo = 0; grupos_fechados++; signal(&cv_noel); }
    while (grupos_concluidos <= g && !encerrar) wait(&cv_elfos, &mutex);
    unlock(&mutex);
}

// Noel
lock(&mutex);
while (!encerrar) {
    int renas_ok = renas_prontas == 9, elfos_ok = proximo_grupo < grupos_fechados;
    if (!renas_ok && !elfos_ok) { wait(&cv_noel, &mutex); continue; }
    if (renas_ok && !grupo_esperou_demais()) {           // renas primeiro, com aging
        renas_prontas = 0;
        unlock(&mutex); preparar(5 ms); lock(&mutex);
        viagens_feitas++; broadcast(&cv_renas);
    } else {
        proximo_grupo++;
        unlock(&mutex); ajudar(3 ms); lock(&mutex);
        grupos_concluidos++; broadcast(&cv_elfos);
    }
}
unlock(&mutex);
```

**O que mudaria nas medições:**
- a vazão seria medida numa **janela de tempo** (regime permanente), sem o custo fixo inicial do G1;
- o p95 teria centenas de amostras e seria um percentil de verdade, não o máximo;
- daria para **medir starvation**: a espera dos elfos crescendo sem limite sem aging, e ficando limitada com aging.

## 7. Violação de prioridade

- **Modo normal:** `escolhe_renas = renas_ok` (`noel.c:117`), e a leitura (`noel.c:89-90`) e a decisão acontecem **na mesma seção crítica**. Não há como as renas estarem prontas no estado lido e Noel escolher elfos. [DESCARTADO]
- **Detector:** `noel.c:118-119` conta `violacoes_prioridade`. Ele **funciona**: no modo `--ingenua` contou 2 violações [CONFIRMADO 2026-10-28].
- **Sutileza de definição:** uma rena **bloqueada no `lock`** (`rena.c:23`) no instante da decisão ainda não chegou para o programa. Noel ajudar um grupo nesse momento é correto.

## 8. Atendimento de quantidade errada de elfos

- **Garantia:** o grupo só vira `PRONTO` quando `n == 3` (`elfo.c:45-47`), e Noel só atende grupos entre `proximo_grupo` e `grupos_fechados` (`noel.c:90`). Inscrição, fechamento e avanço de `grupo_aberto` ocorrem **sem soltar o mutex** (`elfo.c:34-51`).
- **Caso de borda:** no **último** grupo, `grupo_aberto` não avança (`elfo.c:50`). Um elfo extra encontraria esse grupo fechado, cairia em `elfo.c:36-39` e contaria uma violação sem se inscrever. Isso não acontece porque `--elfos` é sempre múltiplo de 3 (`main.c:98`).
- **Classificação:** [DESCARTADO].

## 9. Viagem antes das 9 renas

`renas_ok` exige `renas_prontas == NUM_RENAS` (`noel.c:89`). No modo ingênuo, `escolhe_renas = !elfos_ok`, e só se chega à decisão se `renas_ok || elfos_ok` (`noel.c:100`). Então `!elfos_ok` implica `renas_ok`, e a regra continua garantida. A checagem `noel.c:21-22` é defensiva. [DESCARTADO]

## 10. Encerramento prematuro ou threads que não terminam

- Noel só sai do laço com as duas demandas concluídas (`noel.c:86-87`) ou no timeout.
- Elfos e renas só saem quando o próprio predicado vale, ou com `abortar`.
- A main faz join de **todas** as 1 + 9 + N threads (`main.c:215-219`) antes de destruir os mecanismos (`main.c:222`) e de ler os resultados.
- Os CSVs são gravados depois dos joins, então nenhuma thread escreve enquanto a exportação lê.
- **Classificação:** [DESCARTADO]. Teste do timeout com 5 ms: status `timeout`, sem travar [CONFIRMADO 2026-10-28].

## 11. Defeitos reais (não são de sincronização, mas um avaliador pode apontar)

1. **Retornos de inicialização ignorados** (`main.c:131-139`): `pthread_mutex_init`, `pthread_cond_init` e `pthread_condattr_setclock` retornam códigos de erro que ninguém confere. Com atributos padrão, falhar é improvável, mas a boa prática é verificar.
2. **Caminho de erro do `pthread_create`** (`main.c:187-204`): ao falhar, `main` retorna 1 sem joins e sem destruir os mecanismos. As threads já criadas estão bloqueadas em `cv_largada` e morrem com o processo, então nada trava, mas também não há limpeza.
3. **Invariantes "por construção":** algumas checagens nunca podem disparar com o código atual, então "0 violações" nelas **não prova** nada sozinho:
   - `noel.c:111` (`ajuda_em_curso` na decisão): `preparar_viagem`/`ajudar_grupo` sempre zeram a flag antes de retornar (`noel.c:38`, `70`), e só Noel decide.
   - `noel.c:48` (grupo com ≠ 3 ou fora de `PRONTO`), `noel.c:21` (< 9 renas) e `elfo.c:36` (invasão) também são garantidas pela lógica.
   - Elas valem como **asserções de segurança**: disparariam se uma mudança futura quebrasse a lógica. A prova de que o detector de prioridade funciona é o `--ingenua` (2 violações detectadas).
4. **Medida da espera:** `t_pedido` é gravado **depois** de o elfo obter o mutex (`elfo.c:32`), não no instante em que ele acorda. O tempo de disputa pelo mutex antes disso (microssegundos) fica fora da espera medida.
