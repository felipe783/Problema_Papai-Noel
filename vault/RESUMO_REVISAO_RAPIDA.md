# Resumo para revisão rápida: Problema do Papai Noel (Tema 11)

> **Vai apresentar agora? Leia a [seção 10](#10-revisão-de-um-minuto) primeiro.**
>
> Este resumo trata da **versão finita** (`tema11_papai_noel/`), que é a do trabalho. As linhas citadas são de `tema11_papai_noel/src/`, conferidas no código em 2026-10-28. Apresentação atual: `tema11_papai_noel/apresentacao/apresentacao_papai_noel.pptx` (v4, 31 slides).
>
> ⚠️ **O mais importante:** o código usa **1 mutex + 4 variáveis de condição** e **nenhum semáforo**. Quando a pergunta falar de semáforo, explique o conceito e diga que não usamos.

---

## 1. Visão geral

- **O que é:** um problema clássico de sincronização (Trono, 1994; Downey). Noel dorme e só pode ser acordado por **um grupo de exatamente 3 elfos** ou pela chegada das **9 renas**. Quando as duas demandas estão prontas, **as renas têm prioridade**.
- **Objetivo da simulação:** implementar as regras em **C11 + pthreads** sem espera ocupada e medir vazão, espera dos elfos e tempo de resposta às renas (25 execuções, gráficos G1–G4).
- **Participantes:** 1 thread Noel, 9 threads rena e N threads elfo (N múltiplo de 3, de 3 a 300), mais a `main`, que cria as threads e coordena a largada.
- **Problema de concorrência que demonstra:** **condição de corrida** no estado compartilhado (contadores e grupos), mais **espera e aviso por evento** (dormir até uma condição ficar verdadeira) e uma **política de prioridade sem preempção**.
- **Versão finita:** há uma única viagem e cada elfo faz um único pedido. Depois da viagem e de todos os grupos, o programa termina.

## 2. Funcionamento da simulação

**Noel** (`noel.c`)
1. Trava o mutex e espera a largada.
2. Laço: se a viagem e todos os grupos já foram concluídos, sai.
3. Calcula `renas_ok` e `elfos_ok`. Se nenhum for verdadeiro, dorme em `cv_noel`.
4. Se algum for verdadeiro, decide: **renas primeiro**. Prepara a viagem (5 ms) ou ajuda o próximo grupo da fila (3 ms).
5. Durante a tarefa, **solta o mutex e só dorme**: não olha nada e não é interrompido.
6. Ao terminar, marca a tarefa como concluída, faz `broadcast` para liberar quem esperava e volta ao passo 2.

**Renas** (`rena.c`)
1. Esperam a largada e dormem até `renas_ms` (simula a chegada).
2. Com o mutex: `renas_prontas++`. **A 9ª** grava `t_nona` e dá `signal(cv_noel)`.
3. Dormem em `cv_renas` até `viagem_concluida`.

**Elfos** (`elfo.c`)
1. Esperam a largada e dormem até `10 + id` ms (o elfo *i* chega em 10 + *i* ms).
2. Com o mutex: entram no grupo `grupo_aberto`.
3. **O 3º elfo** marca o grupo `GRUPO_PRONTO`, faz `grupos_fechados++`, avança `grupo_aberto` e dá `signal(cv_noel)`.
4. Dormem em `cv_elfos` até o **seu** grupo estar `GRUPO_CONCLUIDO`.

**Condições para Noel acordar e agir**
- `renas_ok = renas_prontas == 9 && !viagem_iniciada` (`noel.c:89`).
- `elfos_ok = proximo_grupo < grupos_fechados` (`noel.c:90`): existe um grupo fechado ainda não atendido.
- Ou o **timeout de segurança** (2000 ms) do `pthread_cond_timedwait`.

**Quando as condições valem:** Noel lê as duas com o mutex e escolhe `escolhe_renas = renas_ok` (`noel.c:117`). Se vale, prepara a viagem. Senão, atende o grupo `proximo_grupo++` em ordem FIFO.

**Volta a esperar:** ao fim de cada tarefa, Noel volta ao **topo do laço** e reavalia o estado **antes** de dormir. Se algo ficou pronto enquanto ele trabalhava, atende sem precisar de aviso.

## 3. Conceitos essenciais

| Conceito | O que é | Para que serve aqui | O que lembrar |
|---|---|---|---|
| **Thread** | fluxo de execução dentro de um processo, que compartilha a memória dele | cada personagem é uma thread; todas compartilham a `Oficina o` | threads compartilham memória, e por isso precisam de sincronização |
| **Concorrência** | tarefas com tempos de vida sobrepostos (não necessariamente no mesmo instante) | Noel, renas e elfos estão "em andamento" ao mesmo tempo | concorrência ≠ paralelismo; com 1 núcleo ainda há corrida |
| **Seção crítica** | trecho que acessa dados compartilhados e não pode ser intercalado | tudo entre `lock` e `unlock` (inscrição do elfo, `renas_prontas++`, decisão do Noel) | só uma thread por vez ali dentro |
| **Condição de corrida** | resultado depende do entrelaçamento das threads | sem lock, duas renas leem 7 e gravam 8, e o contador nunca chega a 9 | `x++` = ler, somar, gravar: 3 passos interrompíveis |
| **Exclusão mútua (mutex)** | cadeado **com dono**: só quem travou destrava | `o->mutex` protege **todo** o estado da `Oficina` | torna "testar e alterar" indivisível |
| **Semáforo** | contador com `wait` (decrementa, bloqueia em 0) e `post` (incrementa), **sem dono** e **com memória** | **não é usado**; só aparece na comparação com a solução clássica (Downey) | valor inicial define o comportamento (1 = tranca, 0 = espera aviso) |
| **Variável de condição** | fila de espera ligada a um mutex, **sem valor e sem memória** | `cv_largada`, `cv_noel`, `cv_elfos` e `cv_renas`: dormir até um predicado valer | sempre `while (!predicado) wait`; a verdade está no estado |
| **Bloqueio / desbloqueio** | thread sai da CPU até um evento (mutex livre, `signal`, timer) | no `lock` ocupado, no `cond_wait` e no `clock_nanosleep` | bloqueada ≠ encerrada; não gasta CPU |
| **Sincronização / coordenação** | impor as ordens que importam entre threads | o 3º elfo/a 9ª rena avisam Noel; Noel avisa elfos e renas | dois pilares: exclusão mútua + esperar/avisar |
| **Espera e sinalização** | `cond_wait` (dorme soltando o mutex) / `signal` (≥ 1) e `broadcast` (todas) | `signal` em `cv_noel` (só Noel espera); `broadcast` nas outras | aviso sem ninguém esperando se perde, mas o estado fica |
| **Espera ocupada** | girar num laço testando uma condição | **não existe** no código: toda espera é bloqueante | proibida pelo enunciado |
| **Preempção** | o SO tira uma thread da CPU sem ela pedir | é o que **causa** as corridas; continua existindo com mutex | mutex não impede preempção; impede outra thread de **entrar** |
| **Prioridade não preemptiva** | a prioridade só vale no próximo ponto de decisão | Noel não interrompe uma ajuda; decide só no topo do laço | renas vencem **entre** tarefas, nunca **durante** |
| **Deadlock** | espera circular permanente (Coffman) | não ocorre: 1 mutex, sem lock aninhado, `wait` solta o mutex | falta a espera circular |
| **Starvation** | alguém nunca progride porque outros passam na frente | não ocorre na versão finita (1 viagem, grupos em FIFO) | numa versão contínua precisaria de *aging* |

## 4. Sincronização na prática

- **Como se avisa que um evento aconteceu:** quem muda o estado avisa. **Primeiro altera, depois sinaliza, sempre com o mutex.** A 9ª rena faz `signal(cv_noel)` (`rena.c:33`), o 3º elfo também (`elfo.c:53`), e Noel faz `broadcast(cv_renas)` (`noel.c:41`) e `broadcast(cv_elfos)` (`noel.c:73`).
- **Como se evita alteração incorreta do estado:** um **único mutex** protege todos os campos mutáveis da `Oficina` (`comum.h:78`). Inscrever, fechar o grupo e avançar `grupo_aberto` acontecem **na mesma seção crítica** (`elfo.c:27-53`), e por isso um 4º elfo nunca invade o grupo: ele cai no grupo seguinte.
- **Como Noel sabe quando acordar:** ele **não monitora**. Dorme em `cv_noel` e é acordado pelo `signal`. Ao acordar, **readquire o mutex e relê o estado** (`continue` em `noel.c:107` → `noel.c:89-90`). A decisão vem do **estado**, não do aviso.
- **Como esperar sem testar continuamente:** `pthread_cond_wait`/`timedwait` **soltam o mutex e dormem numa operação atômica**. A thread sai da fila de prontas do SO e só volta com um aviso (ou com o timeout, no caso do Noel). Os `clock_nanosleep` só **simulam durações**; nenhuma coordenação depende deles.
- **Aviso perdido não é bug:** se o 3º elfo sinaliza com Noel ocupado, ninguém ouve, mas `grupos_fechados` ficou gravado. Noel testa o predicado **antes** de dormir.
- **A prioridade vem da regra, não do mutex:** `escolhe_renas = renas_ok` (`noel.c:117`). A versão `--ingenua` usa os **mesmos** mecanismos e viola a regra.

**Papel de cada mecanismo**

| Mecanismo | Quem espera | Predicado da espera | Quem avisa |
|---|---|---|---|
| `mutex` | qualquer thread no `lock` | ficar livre | o `unlock` da dona |
| `cv_largada` | threads (`main.c:29-30`) e main (`main.c:208-209`) | `largada == 1` / `threads_prontas == total_threads` | `broadcast` das threads (`main.c:28`) e da main (`main.c:212`) |
| `cv_noel` | só Noel (`noel.c:101`, `timedwait`) | `renas_ok \|\| elfos_ok` ou prazo vencido | 9ª rena (`rena.c:33`), 3º elfo (`elfo.c:53`) |
| `cv_elfos` | elfos de **todos** os grupos (`elfo.c:57-58`) | **seu** grupo `GRUPO_CONCLUIDO` ou `abortar` | Noel (`noel.c:73`, `143`) |
| `cv_renas` | as 9 renas (`rena.c:36-37`) | `viagem_concluida` ou `abortar` | Noel (`noel.c:41`, `144`) |

## 5. Código: o que preciso lembrar

### 5.1 Mecanismos e estado compartilhado

| Nome | Tipo | Valor ou estado inicial | Inicialização | Espera, adquire, libera ou sinaliza | Finalidade |
|---|---|---|---|---|---|
| `mutex` | `pthread_mutex_t` (declarado em `comum.h:82`) | **destravado, sem dono**, atributos padrão (`NULL`) | `pthread_mutex_init(&o->mutex, NULL)` em **`main.c:131`**; destruído em `main.c:150` (chamado em `main.c:222`) | lock/unlock: main `207/213`; Noel `81/145` (solta em `31/33` e `60/62`); rena `17/19`, `23/25·38`; elfo `21/23`, `27/29·38·59` | protege **todo** o estado |
| `cv_largada` | `pthread_cond_t` (`comum.h:83`) | fila vazia (cond var não tem valor) | `main.c:132` | wait `main.c:30` e `209`; broadcast `main.c:28` e `212` | barreira caseira de início |
| `cv_noel` | `pthread_cond_t` com `CLOCK_MONOTONIC` (`comum.h:84`) | fila vazia | `main.c:136-140` (`setclock` na `138`) | `timedwait` `noel.c:101`; signal `rena.c:33`, `elfo.c:53` | Noel dorme até ter trabalho; timeout |
| `cv_elfos` | `pthread_cond_t` (`comum.h:85`) | fila vazia | `main.c:133` | wait `elfo.c:58`; broadcast `noel.c:73`, `143` | elfos esperam o fim da ajuda |
| `cv_renas` | `pthread_cond_t` (`comum.h:86`) | fila vazia | `main.c:134` | wait `rena.c:37`; broadcast `noel.c:41`, `144` | renas esperam o fim da preparação |
| `renas_prontas` | `int` | 0 (`memset`, `main.c:109`) | — | `++` em `rena.c:28`; lido em `noel.c:89` | contar as renas |
| `grupos[g]` (`n`, `membros`, `estado`) | `Grupo` | `n = 0`, `GRUPO_ABERTO` (`calloc`, `main.c:116`) | — | elfo `elfo.c:41`, `47`; Noel `noel.c:51`, `68` | grupo de 3 elfos |
| `grupo_aberto`, `grupos_fechados`, `proximo_grupo` | `int` | 0, 0, 0 (`memset`) | — | elfo `elfo.c:34`, `49-51`; Noel `noel.c:90`, `128` | fila FIFO de grupos com id |
| `viagem_iniciada`, `viagem_concluida` | `int` | 0 | — | Noel `noel.c:24`, `37`; rena lê em `rena.c:36` | uma viagem só, e liberar as renas |
| `largada`, `threads_prontas` | `int` | 0; `total_threads = 1 + 9 + N` (`main.c:112`) | — | `main.c:27`, `211` | início comum da medição |
| `abortar` | `int` | 0 | — | `noel.c:103`; lido em `elfo.c:28/57`, `rena.c:24/36` | timeout: todos saem |
| `estado` (de Noel) | `EstadoNoel` | `NOEL_DORMINDO` (`main.c:113`) | — | `noel.c:25`, `39`, `52`, `71`, `136` | registro em eventos |

### 5.2 Onde fica cada coisa

| O quê | Onde |
|---|---|
| Estado compartilhado (`struct Oficina`) | `comum.h:79-123`; a instância `Oficina o` é local da main (`main.c:171`) |
| Inicialização de tudo | `iniciar_oficina`, `main.c:107-142` (memset 109, mutex 131, cond vars 132-140) |
| Criação das threads (todas antes de qualquer join) | Noel `main.c:187`; renas `main.c:191-197`; elfos `main.c:198-204` |
| Início de cada thread | `thread_noel` (`noel.c:76`), `thread_rena` (`rena.c:12`), `thread_elfo` (`elfo.c:15`) |
| Largada comum | `esperar_largada` (`main.c:25-31`) + main (`main.c:207-213`, grava `t0` na 210) |
| Seções críticas principais | inscrição do elfo `elfo.c:27-59`; contagem das renas `rena.c:23-38`; laço/decisão de Noel `noel.c:81-145` |
| Verificação das condições de despertar | `noel.c:89-90` (`renas_ok`, `elfos_ok`) e `noel.c:100` |
| Decisão e prioridade | `noel.c:117` (`escolhe_renas`), detector de violação `noel.c:118-119` |
| Tarefa sem interrupção | `preparar_viagem` (`noel.c:19-42`, sleep na 32) e `ajudar_grupo` (`noel.c:45-74`, sleep na 61) |
| Sinalização entre threads | `rena.c:33`, `elfo.c:53`, `noel.c:41`, `73`, `143-144`, `main.c:28`, `212` |
| Término normal / timeout | `noel.c:86-87` / `noel.c:101-106` |
| Joins e destruição | `main.c:215-219` e depois `main.c:222` |
| Sleeps de simulação | `dormir_ate_ms`, `tempo.c:43-50` (`clock_nanosleep` absoluto, linha 48) |

### 5.3 Os três trechos para mostrar

```c
// elfo.c:41-53 — o 3º elfo fecha o grupo (tudo com o mutex)
gr->membros[gr->n++] = id;
if (gr->n == TAM_GRUPO) {
    gr->estado = GRUPO_PRONTO;  o->grupos_fechados++;
    if (o->grupo_aberto + 1 < o->n_grupos) o->grupo_aberto++;
    pthread_cond_signal(&o->cv_noel);
}

// noel.c:89-90, 100-101, 117 — Noel decide
int renas_ok = o->renas_prontas == NUM_RENAS && !o->viagem_iniciada;
int elfos_ok = o->proximo_grupo < o->grupos_fechados;
if (!liberado || (!renas_ok && !elfos_ok))
    pthread_cond_timedwait(&o->cv_noel, &o->mutex, &limite);  // + continue
int escolhe_renas = c->ingenua ? !elfos_ok : renas_ok;

// rena.c:36-37 — padrão de espera
while (!o->viagem_concluida && !o->abortar)
    pthread_cond_wait(&o->cv_renas, &o->mutex);
```

## 6. Fluxo completo da execução

1. **Argumentos:** `ler_args` (`main.c:75-105`) valida `--elfos` (múltiplo de 3) e `--renas-ms`.
2. **Inicialização:** `memset` zera a `Oficina` (todos os predicados em 0), `calloc` deixa os grupos `ABERTO`, e o mutex e as 4 cond vars são inicializados (`main.c:109-140`), **antes** de qualquer thread.
3. **Criação:** 1 Noel, 9 renas e N elfos (`main.c:187-204`).
4. **Largada:** cada thread faz `threads_prontas++`, dá `broadcast` e dorme em `cv_largada`. Quando todas estão prontas, a main grava `t0` (`CLOCK_MONOTONIC`), faz `largada = 1` e dá `broadcast` (`main.c:207-213`).
5. **Chegadas simuladas:** elfos e renas dormem **sem o mutex** até o instante de chegada. Noel dorme em `cv_noel`.
6. **Eventos alteram o estado:** elfos se inscrevem e o 3º fecha o grupo; renas incrementam o contador. A 9ª rena e cada 3º elfo dão `signal(cv_noel)`.
7. **Noel reavalia** `renas_ok`/`elfos_ok` com o mutex e decide: **renas primeiro**.
8. **Tarefa:** Noel solta o mutex, dorme 5 ms (viagem) ou 3 ms (ajuda), retoma o mutex, marca concluído e faz `broadcast` em `cv_renas` ou `cv_elfos`.
9. **Quem foi liberado** acorda, readquire o mutex (um por vez), testa o **seu** predicado e termina.
10. **Repete** até `viagem_concluida && grupos_concluidos == n_grupos` (`noel.c:86`), ou até o timeout (`abortar = 1`).
11. **Encerramento:** Noel faz `broadcast` final em `cv_elfos` e `cv_renas` e solta o mutex (`noel.c:135-145`).
12. **Main:** joins de todas as threads → destrói os mecanismos → calcula métricas → exporta os CSVs → imprime o resumo (`main.c:215-236`).

**Linha do tempo real (referência E06_R10_rep1, 6 elfos, renas em 10 ms):** elfo 0 em 10,080 → 9ª rena em 10,091 → decisão "viagem" em 10,108 → grupo 1 pronto (12,07) e grupo 2 pronto (15,06) **durante** a preparação → fim da viagem em 15,185 → grupo 1 em 15,200 → grupo 2 em 18,279 → encerramento em 21,362 ms.

## 7. Perguntas do professor

As 8 perguntas originais (P1–P8) e as perguntas sobre o código vêm de `vault/Apresentacao/Perguntas da Apresentação (Papai Noel).md` e do banco do guia v4.

### Perguntas originais

| # | Pergunta | Resposta curta | Slide |
|---|---|---|---|
| P1 | O que é um problema de sincronização? | Threads compartilham dados, e a correção depende da ordem de execução. Resolver = **exclusão mútua** + **esperar/avisar** sem gastar CPU e sem travar. | 3, 4 |
| P2 | Como se relaciona com o SO? | O SO escalona e interrompe as threads (é isso que cria as corridas) e também fornece os mecanismos, tirando da CPU a thread bloqueada. | 3, 7 |
| P3 | O que são mutex e semáforo? | Mutex: cadeado com dono, para exclusão mútua, que começa destravado. Semáforo: contador `wait`/`post`, sem dono, com memória. **Usamos mutex + cond vars, nenhum semáforo.** | 5, 29 |
| P4 | `if` com contador × mutex? | O `if` testa e depois altera, e outra thread pode entrar entre os dois passos. O mutex torna o par indivisível. Exemplo: o elfo testa a vaga e se inscreve dentro do mutex. | 4, 13 |
| P5 | Relação com threads/processos no SO? | Noel = recurso único; renas e elfos = clientes com prioridade; grupo = lote; não interromper a ajuda = escalonamento **não preemptivo**; renas sempre de volta = starvation. | 7 |
| P6 | Princípios de uma boa solução? Atende? Poderia melhorar? | Exclusão mútua, progresso, espera limitada (na versão finita), sem hipótese de velocidade, sem espera ocupada e sem deadlock: **atendidos**. Robustez **parcial** (retornos de `init` não verificados). Melhorias: verificar retornos, cond var por grupo, prazo na largada, *aging* numa versão contínua. | 19, 27 |
| P7 | Starvation e deadlock aparecem? | Deadlock não: 1 mutex, sem espera circular. Starvation não na versão finita (1 viagem, FIFO); numa contínua, a prioridade absoluta às renas poderia causá-la. | 20 |
| P8 | Como apresentar os gráficos? | Fixo → variou → quantas execuções → tendência → que parte do código explica → a diferença supera a variação? E sempre: **dados mostram, não provam**. | 21–26 |

### Perguntas sobre o código e prováveis

- **Usa mutex, semáforo ou ambos?** Só **1 mutex + 4 cond vars**. Nenhum `sem_t` nem `pthread_barrier` (confirmado por `grep`).
- **Onde o mutex começa a ser usado? Valor inicial?** Declarado em `comum.h:82` e inicializado em **`main.c:131`** com `pthread_mutex_init(&o->mutex, NULL)`: **destravado, sem dono**. O primeiro `lock` é o do Noel (`noel.c:81`), da rena (`rena.c:17`) ou do elfo (`elfo.c:21`), o que rodar primeiro. O `memset` **não** conta como inicialização, e o código **não** usa `PTHREAD_MUTEX_INITIALIZER`.
- **Por que mutex e não só uma variável (flag)?** `while (ocupado); ocupado = 1;` sofre a mesma corrida (testar e atribuir são 2 passos) e ainda é espera ocupada. O mutex usa uma instrução **atômica** do hardware e põe para dormir quem perde.
- **Diferença mutex × semáforo?** Mutex: tem dono, não tem valor, serve para exclusão. Semáforo: sem dono (qualquer thread dá `post`), tem contador e memória, e seu valor inicial muda o comportamento. Um semáforo binário imita o mutex, mas sem dono.
- **Diferença ao inicializar?** `pthread_mutex_init(&m, NULL)` não recebe número: começa sempre livre. `sem_init(&s, 0, valor)` recebe o contador inicial. No projeto só existe o primeiro.
- **E se o valor inicial do semáforo fosse outro?** (solução clássica, **não** o nosso código) `mutex = 0` trava tudo e `= 2` perde a exclusão; `santaSem = 1` faz Noel acordar sem demanda. No nosso código, o equivalente seria um predicado com valor inicial errado: `renas_prontas = 1` faria a viagem sair com 8 renas.
- **O que acontece ao tentar travar um mutex já travado?** A thread **bloqueia** dentro de `pthread_mutex_lock` (sem gastar CPU) até a dona soltar. **Não termina** e não dá erro. A POSIX não garante ordem FIFO.
- **O SO pode interromper uma thread durante uma operação?** **Sim**, entre quaisquer duas instruções de máquina, **inclusive dentro da seção crítica**. O mutex não impede a preempção; impede que **outra** thread entre na seção enquanto a dona estiver fora da CPU.
- **Por que ocorre condição de corrida?** Porque `x++` são 3 passos (ler, somar, gravar) e o escalonador pode intercalar as threads entre eles. Exemplo: duas renas leem 7 e gravam 8.
- **Como as threads sabem quando esperar ou continuar?** Pelo **predicado** testado em `while` com o mutex. Se é falso, dormem (`cond_wait` solta o mutex). Ao acordar, retomam o mutex e **testam de novo**.
- **Por que `while` e não `if`?** Por causa do acordar espúrio, do `broadcast` que acorda elfos de outros grupos e do estado que pode mudar entre o aviso e a reaquisição do mutex.
- **Como Noel sabe que deve acordar?** A 9ª rena ou o 3º elfo mudam o estado e dão `signal(cv_noel)`. Noel acorda, readquire o mutex e relê `renas_ok`/`elfos_ok`. Se estava ocupado, vê o estado ao voltar ao topo do laço.
- **Por que `signal` em `cv_noel` e `broadcast` nas outras?** Em `cv_noel` só Noel espera. Em `cv_elfos` há elfos de vários grupos, e em `cv_renas` há 9 renas. Na largada, um `signal` poderia acordar uma thread em vez da main.
- **Como garante a prioridade sem interromper a ajuda?** Só Noel decide, com o mutex, testando as renas primeiro (`noel.c:117`). Durante a tarefa ele só dorme. A rena que chega nesse meio-tempo é vista no topo do laço. Teste de prioridade: **PASSOU**; versão ingênua: **2 violações** detectadas.
- **Como impede um 4º elfo?** O 3º elfo fecha o grupo e avança `grupo_aberto` na **mesma** seção crítica, e o 4º cai no grupo seguinte. Ele **não é rejeitado nem fica esperando**.
- **Se Noel solta o mutex na ajuda, alguém "rouba" o grupo?** Não. Só a thread Noel executa tarefas, o grupo está `GRUPO_EM_AJUDA` e `proximo_grupo` já avançou.
- **O que aconteceria sem sincronização?** Contadores perderiam atualizações (a viagem nunca sairia → timeout), grupos teriam 4 elfos e Noel decidiria com um retrato velho do estado. Sem cond var, a alternativa seria espera ocupada.
- **Por que `CLOCK_MONOTONIC` na `cv_noel`?** O prazo é `t0 + timeout`, e `t0` vem desse relógio. Ele também não muda se alguém ajustar a hora do sistema.
- **O timeout é admitir deadlock?** Não. É uma rede de segurança, que nunca disparou em 25 + 300 execuções. Limite: não salva um mutex nunca liberado, porque o `timedwait` precisa readquiri-lo.
- **Um único mutex é gargalo?** Não com ~22 threads e seções críticas de µs (resposta às renas ≈ 20 µs). Com milhares, valeria separar os locks com ordem fixa de aquisição.
- **Os resultados provam a correção?** Não. Mostram que as regras valeram nas execuções. A garantia vem da análise do código. Na matriz houve **0 decisões com disputa**: a prioridade foi testada só pelo `--teste-prioridade` e pelo `--ingenua`.
- **E se renas e elfo chegarem exatamente juntos?** Quem pega o mutex primeiro define o que Noel vê. Uma rena presa na fila do mutex ainda "não chegou" para o programa, e isso **não é violação**.

## 8. Gráficos e diagramas

Os PNGs estão em `tema11_papai_noel/graficos/`. Os números vêm de `dados/` (25/25 execuções `ok`).

| Gráfico | O que mostra | Ideia para lembrar |
|---|---|---|
| **G1** `G1_vazao_elfos.png` (slide 22) | vazão × nº de elfos (3, 6, 12), renas em 10 ms | **163 → 281 → 436 pedidos/s**: mais elfos diluem o custo fixo inicial (~15 ms) |
| **G2** `G2_p95_renas.png` (slide 23) | p95 da espera dos elfos × chegada das renas (antes/junto/depois) + resposta às renas | p95 **2,1 → 5,2 ms** só com as renas **junto**: é o preço da prioridade. Renas atendidas em **~20 µs** (painel em **µs**, não ms!) |
| **G3** `G3_p95_grupo.png` (slide 24) | p95 por grupo na referência | grupos esperam **igual** (5,12 × 5,20 ms): o atraso se propaga sem crescer. Contrariou a intuição, e vale dizer isso |
| **G4** `G4_linha_tempo.png` (slide 25) | estados de Noel ao longo do tempo (E06_R10_rep1) | grupos ficam prontos **durante** a viagem e esperam **sem interrompê-la** |
| Slide 18 | correta × ingênua | mesmos mecanismos, regra invertida: **0 × 2 violações**; resposta às renas 18 µs × 6,145 ms. A ingênua terminou antes e **mesmo assim está errada** |
| Slides 16 e 31 | rena durante a ajuda; empate de chegada | execuções **avulsas**, sem CSV salvo: não apresentar como rodada oficial |
| Slide 4 | sem mutex × com mutex | **hipotético** (o programa nunca roda sem mutex) |

- **p95 com 3 ou 6 amostras = o máximo.**
- A variação entre repetições é < 1%, porque o cenário é dirigido pelo relógio; as sementes são só o id da repetição.

## 9. Erros comuns e pegadinhas

- ❌ "Usamos semáforos." → ✅ **1 mutex + 4 variáveis de condição**, zero semáforos.
- ❌ "A cond var começa em 0." → ✅ Cond var **não tem valor**. Quem tem valor inicial são os predicados (zerados pelo `memset`).
- ❌ Confundir o valor inicial de semáforo com o estado do mutex. → ✅ O mutex não tem número: começa **destravado**. O semáforo começa num número que muda o comportamento.
- ❌ "O mutex mantém/executa o processo" ou "Noel fica com a chave e monitora". → ✅ O mutex só **protege dados**. Noel segura o mutex por µs, solta para trabalhar e **dorme** em `cv_noel`; quem muda o estado avisa.
- ❌ "A thread bloqueada termina/morre." → ✅ Ela **dorme** (sai da CPU) e volta quando o mutex libera ou chega um aviso.
- ❌ "Concorrência = execução simultânea." → ✅ Concorrência = tarefas sobrepostas no tempo; simultaneidade física é **paralelismo**. Com 1 núcleo ainda há corrida.
- ❌ "Com mutex não há preempção." → ✅ A preempção continua. O mutex só impede outra thread de **entrar** na seção crítica.
- ❌ "O mutex (ou a cond var) garante a prioridade." → ✅ Quem garante é a **regra** `escolhe_renas = renas_ok`. O mutex só garante que ela se aplica a um estado consistente.
- ❌ Confundir a **condição** de despertar (`renas_ok || elfos_ok`) com o **mecanismo** (`cv_noel` + `signal`). → ✅ O aviso não carrega informação; quem decide é o estado lido com o mutex.
- ❌ "As renas interrompem Noel." → ✅ A prioridade é **não preemptiva**: vale só no topo do laço.
- ❌ "O 4º elfo é rejeitado/espera." → ✅ Ele **forma o próximo grupo** (diferente da catraca `elfTex` da solução de Downey).
- ❌ "`signal` acorda exatamente uma thread." → ✅ Acorda **pelo menos uma**.
- ❌ Confundir a fila do mutex (espera **a chave**, µs) com a fila da cond var (espera **um evento**, ms).
- ❌ "Os testes provam que não há corrida." → ✅ Mostram; não provam. TSan/Helgrind **não foram rodados**.
- ❌ "Houve disputa na matriz." → ✅ Na matriz, **0 decisões com disputa** (`dados/log_execucao.txt`). A disputa foi forçada pelo `--teste-prioridade`.
- ❌ Ler o painel de resposta às renas do G2 como ms (é **µs**).

## 10. Revisão de um minuto

**Ideias essenciais**
1. **1 mutex + 4 cond vars** (`cv_largada`, `cv_noel`, `cv_elfos`, `cv_renas`), **nenhum semáforo**.
2. O mutex nasce **destravado** em **`main.c:131`**, antes de qualquer thread.
3. Toda espera: `lock → while (!predicado) wait → age → unlock`. O `wait` solta o mutex e dorme atomicamente.
4. O 3º elfo **fecha o grupo e avança `grupo_aberto` na mesma seção crítica**, e o 4º vai para o próximo grupo.
5. A 9ª rena / o 3º elfo **alteram o estado e avisam** `cv_noel`. Noel relê o estado; a verdade está no estado, não no aviso.
6. **Prioridade** = `escolhe_renas = renas_ok` (`noel.c:117`), lida e aplicada com o mutex. **Não preemptiva**: a ajuda nunca é interrompida.
7. Sem deadlock (1 mutex, sem espera circular), sem starvation na versão finita, sem espera ocupada. Robustez parcial.
8. 25/25 `ok`; G1 163 → 436; G2 2,1 → 5,2 ms; renas em ~20 µs; teste **PASSOU**; ingênua **2 violações**.

**Funcionamento em 10 linhas**
```
main inicializa mutex + 4 cond vars → cria Noel, 9 renas, N elfos
todas esperam a largada; a main grava t0 e libera todas (broadcast)
elfos chegam e entram no grupo aberto; o 3º fecha o grupo e dá signal(cv_noel)
renas chegam e contam; a 9ª dá signal(cv_noel)
Noel acorda, retoma o mutex e lê renas_ok / elfos_ok
renas_ok? → prepara a viagem (5 ms)  |  senão → ajuda o próximo grupo (3 ms)
durante a tarefa: sem mutex, sem decisão, sem interrupção
fim → marca concluído → broadcast(cv_renas ou cv_elfos)
volta ao topo, reavalia; tudo concluído → broadcast final → sai
main faz os joins → destrói os mecanismos → métricas → CSVs
```

**Mutex × semáforo**

| | Mutex | Semáforo |
|---|---|---|
| Dono | sim (só quem travou destrava) | não (qualquer thread dá `post`) |
| Valor | não tem; começa **destravado** | contador inicial (`sem_init(&s, 0, v)`) |
| Memória de avisos | não | sim (o contador guarda) |
| Uso típico | exclusão mútua | contar recursos / sinalizar eventos |
| No projeto | **1** (`o->mutex`) | **0** |

**Problema principal:** **condição de corrida** no estado compartilhado (contadores e grupos) + coordenar a espera por eventos sem espera ocupada, aplicando **prioridade às renas sem interromper a ajuda**.

**Frase final:** *"Um mutex garante um estado consistente, as variáveis de condição fazem as threads dormirem até esse estado mudar, e uma regra de decisão aplicada por Noel garante a prioridade das renas."*

---

### Fontes e divergências (para não ser pego de surpresa)

- **Fontes:** código de `src/` (todos os `.c`/`.h` principais), `README.md`, as notas de `vault/` e os textos dos slides da v4 e do `relatorio.pdf`.
- **Divergências encontradas:**
  - O `Guia de Estudo Teórico` usa uma **implementação de referência** (`PTHREAD_MUTEX_INITIALIZER`, 3 cond vars, nomes como `renas_chegaram`) que **não é o código real**. Use-o só para teoria.
  - O `Guia Completo da Apresentação` é da **v3 (37 slides)**: os números de slide não batem com a v4 atual (31 slides).
  - O slide 31 (empate) diz **12/30** viagens; a reexecução registrada no vault deu **10/30**, e outra nota registra **8/30**. A proporção varia entre rodadas e o CSV não foi salvo; o que não muda é **0 violações**.
  - A nota `Lógica e Fluxo` chama a referência de "com disputa", mas o log mostra **0 decisões com disputa**. Lá, "disputa" quer dizer elfos e renas chegando juntos (disputando o mutex), não uma decisão com as duas demandas prontas.
  - `README.md` e `relatorio.pdf` ainda têm `[Integrante 1/2/3]`; o slide 1 da v4 já tem o nome. O README também cita um `slides.pptx` que não está mais na pasta.
  - O **enunciado oficial** e o **tempo da apresentação** não estão documentados [NÃO VERIFICADO].
