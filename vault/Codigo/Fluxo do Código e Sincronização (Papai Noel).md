# Fluxo do Código e Sincronização (Papai Noel)

A execução **fase a fase**, do `main()` ao último `pthread_join`, mostrando em cada fase quem protege, quem espera, quem avisa e por quê. As outras notas se dividem assim:

| Nota | Ângulo |
|---|---|
| [[Sincronização no Código (Papai Noel)]] | **mecanismo a mecanismo**: o mutex e cada cond var em profundidade |
| [[Lógica e Fluxo (Papai Noel)]] | regras, estados de Noel e linhas do tempo da rodada oficial |
| [[Riscos de Sincronização (Papai Noel)]] | o que pode dar errado, com classificação |
| [[Guia da Pasta src (Papai Noel)]] | cada arquivo e bloco do código |

Índice: [[_Papai-Noel]].

> Código lido em 2026-10-28; as referências `arquivo:linha` são de `tema11_papai_noel/src/`. As linhas do tempo marcadas como **verificação** vêm de execuções feitas em 2026-10-28 numa pasta temporária, **fora** da rodada oficial de `dados/` [CONFIRMADO 2026-10-28]. Os tempos variam alguns µs entre execuções; a **ordem** dos eventos é o que importa.

## 1. Cinco papéis que não se confundem

Na apresentação, separe sempre **o que** cada trecho faz. O mesmo mecanismo pode aparecer em papéis diferentes, e um papel pode não depender de nenhum mecanismo específico.

| Papel | Pergunta que responde | Como é feito | Onde |
|---|---|---|---|
| **Proteção de seção crítica** | quem pode ler e alterar o estado agora? | `pthread_mutex_lock` / `unlock` do **único** `mutex` | `main.c:207/213`; `noel.c:81/145` (e o par `31/33`, `60/62`); `elfo.c:21/23`, `27/29·38·59`; `rena.c:17/19`, `23/25·38` |
| **Espera por condição** | quando vale a pena olhar o estado de novo? | `while (!predicado) pthread_cond_wait(&cv, &mutex)` | `main.c:29-30` e `208-209` (`cv_largada`); `noel.c:100-101` (`cv_noel`, com prazo); `elfo.c:57-58` (`cv_elfos`); `rena.c:36-37` (`cv_renas`) |
| **Notificação** | como avisar que o estado mudou? | `pthread_cond_signal` / `broadcast`, sempre **depois** de alterar o estado e **com** o mutex | `main.c:28`, `212`; `elfo.c:53`; `rena.c:33`; `noel.c:41`, `73`, `143-144` |
| **Aplicação da prioridade** | renas ou elfos? | **regra de decisão**, não um mecanismo: `escolhe_renas = renas_ok`, lida e aplicada na mesma seção crítica | `noel.c:89-90`, `117`, `123-132` |
| **Encerramento seguro** | como todos terminam sem ninguém ficar preso? | condição de término no topo do laço + broadcasts finais + `abortar` nos predicados + joins antes do destroy | `noel.c:86-87`, `135-145`; `elfo.c:28`, `57`; `rena.c:24`, `36`; `main.c:215-222` |

Três distinções que a banca costuma testar:

1. **Bloquear no mutex ≠ esperar uma condição.** Uma thread parada em `pthread_mutex_lock` quer **acesso exclusivo** e segue assim que o dono soltar. Uma thread em `pthread_cond_wait` **soltou** o mutex e espera **um evento** (o grupo concluído, a viagem concluída). A primeira espera dura microssegundos; a segunda, milissegundos.
2. **O aviso não carrega informação.** Quem decide é o **estado** lido com o mutex (`renas_prontas`, `grupos_fechados`, `estado` do grupo). Por isso um `signal` "perdido" com Noel ocupado não é bug: o estado ficou gravado e Noel o relê no topo do laço.
3. **A prioridade não vem do mutex nem da cond var.** Ela vem da **ordem do teste** em `noel.c:117`. Os mecanismos só garantem que a regra seja aplicada sobre um retrato consistente do estado. Ter mutex e cond vars, por si só, **não** garante a prioridade: a versão `--ingenua` usa exatamente os mesmos mecanismos e viola a regra.

## 2. Cola dos mecanismos

Não há semáforos: a coordenação que, na solução clássica, caberia a eles está nos predicados + cond vars ([[Sincronização no Código (Papai Noel)#3. Semáforos: não são usados]]).

| Mecanismo | Declaração | Inicialização (linha e argumentos) | Estado inicial | Espera / adquire | Libera / sinaliza | Protege ou coordena |
|---|---|---|---|---|---|---|
| `mutex` | `comum.h:82` | `pthread_mutex_init(&o->mutex, NULL)`, `main.c:131`. `NULL` = atributos padrão (não recursivo, privado ao processo) | destravado, sem dono | `lock` nas linhas da tabela 1 | `unlock` nas mesmas | **todo** campo mutável da `Oficina` |
| `cv_largada` | `comum.h:83` | `pthread_cond_init(&o->cv_largada, NULL)`, `main.c:132` | ninguém esperando; predicados `largada = 0`, `threads_prontas = 0` | threads: `main.c:30`; main: `main.c:209` | threads: `broadcast` `main.c:28`; main: `broadcast` `main.c:212` | o sinal de início comum |
| `cv_noel` | `comum.h:84` | `main.c:136-140`: `pthread_condattr_setclock(&at, CLOCK_MONOTONIC)` e `pthread_cond_init(&o->cv_noel, &at)`, para o prazo do `timedwait` usar o mesmo relógio de `t0` | ninguém esperando; `renas_prontas = 0`, `grupos_fechados = 0` | só Noel: `timedwait` `noel.c:101` | 9ª rena: `signal` `rena.c:33`; 3º elfo: `signal` `elfo.c:53` | "há trabalho para Noel" |
| `cv_elfos` | `comum.h:85` | `pthread_cond_init(&o->cv_elfos, NULL)`, `main.c:133` | ninguém esperando; grupos `ABERTO` (`calloc`) | elfos: `elfo.c:58` | Noel: `broadcast` `noel.c:73` (fim de cada ajuda) e `143` (encerramento) | "o grupo do elfo foi concluído" |
| `cv_renas` | `comum.h:86` | `pthread_cond_init(&o->cv_renas, NULL)`, `main.c:134` | ninguém esperando; `viagem_concluida = 0` | renas: `rena.c:37` | Noel: `broadcast` `noel.c:41` (fim da preparação) e `144` | "a viagem foi concluída" |

Todos são destruídos em `destruir_oficina` (`main.c:144-151`), chamada em `main.c:222`, **depois** dos joins.

**O que acontece quando várias threads tentam prosseguir juntas:**
- **No mutex:** uma entra e as outras dormem dentro do `lock`. Quando o dono solta, uma delas é acordada. A POSIX **não garante ordem FIFO**: quem entra depende do escalonador. Por isso a ordem "9ª rena × 3º elfo" varia entre execuções (seção 5.5).
- **Num `broadcast`:** todas as threads da fila acordam, mas cada uma precisa **readquirir o mutex** antes de voltar do `wait`. Elas saem **uma por vez**, e cada uma reavalia o **próprio** predicado. Na `cv_elfos`, os elfos de outros grupos voltam a dormir.
- **Num `signal`:** acorda pelo menos uma thread. Só é usado em `cv_noel`, que tem **um único** consumidor (Noel).

## 3. Fluxo completo

```mermaid
sequenceDiagram
    autonumber
    participant M as main
    participant N as Noel
    participant R as Renas (9)
    participant E as Elfos (N)

    Note over M: ler_args (main.c:166)<br/>iniciar_oficina: memset, calloc,<br/>mutex + 4 cond vars (main.c:107-142)
    M->>N: pthread_create (main.c:187)
    M->>R: pthread_create ×9 (main.c:191-197)
    M->>E: pthread_create ×N (main.c:198-204)
    N->>N: lock · esperar_largada (noel.c:81-82)
    R->>R: lock · esperar_largada · unlock
    E->>E: lock · esperar_largada · unlock
    Note over N,E: cada uma: threads_prontas++ · broadcast(cv_largada) · wait(cv_largada)
    M->>M: lock · while threads_prontas < total: wait (main.c:207-209)
    M-->>N: t0 = agora · largada = 1 · broadcast(cv_largada) (main.c:210-212)
    M-->>R: (mesmo broadcast)
    M-->>E: (mesmo broadcast)
    M->>M: pthread_join(Noel) ... bloqueia (main.c:215)

    N->>N: laço: nada pronto → timedwait(cv_noel) (noel.c:100-101)
    E->>E: dorme até t0 + 10 + id (elfo.c:25)
    R->>R: dormem até t0 + renas_ms (rena.c:21)

    E->>E: lock · inscreve-se em grupos[grupo_aberto] (elfo.c:27-43)
    E-->>N: 3º elfo: PRONTO · grupos_fechados++ · signal(cv_noel) (elfo.c:45-53)
    E->>E: wait(cv_elfos) (elfo.c:57-58)
    R->>R: lock · renas_prontas++ (rena.c:23-28)
    R-->>N: 9ª rena: t_nona · signal(cv_noel) (rena.c:30-33)
    R->>R: wait(cv_renas) (rena.c:36-37)

    N->>N: reavalia renas_ok / elfos_ok (noel.c:89-90)
    alt renas_ok (prioridade, noel.c:117)
        N->>N: preparar_viagem: viagem_iniciada=1 · unlock · dorme preparo_ms · lock
        N-->>R: viagem_concluida=1 · broadcast(cv_renas) (noel.c:37-41)
    else só elfos_ok
        N->>N: ajudar_grupo(proximo_grupo++): EM_AJUDA · unlock · dorme ajuda_ms · lock
        N-->>E: CONCLUIDO · broadcast(cv_elfos) (noel.c:68-73)
    end
    Note over N: volta ao topo do laço e reavalia;<br/>repete até viagem_concluida e todos os grupos concluídos

    N->>N: ENCERRADO · broadcast(cv_elfos, cv_renas) · unlock (noel.c:135-145)
    R->>R: readquirem o mutex um a um · unlock · return
    E->>E: readquirem o mutex um a um · unlock · return
    M->>M: join de todas (main.c:215-219) · destruir_oficina (main.c:222)
    M->>M: calcular_metricas · exportar_csv · printf · código de saída (main.c:224-264)
```

## 4. Fase a fase

### 4.1 Inicialização do programa

```c
// main.c:109, 116, 131-140 (trechos)
memset(o, 0, sizeof *o);                                // todos os predicados começam em 0
o->grupos = calloc((size_t)o->n_grupos, sizeof(Grupo)); // n = 0, estado = GRUPO_ABERTO (0)
pthread_mutex_init(&o->mutex, NULL);
pthread_cond_init(&o->cv_largada, NULL);
pthread_cond_init(&o->cv_elfos, NULL);
pthread_cond_init(&o->cv_renas, NULL);
pthread_condattr_setclock(&at, CLOCK_MONOTONIC);
pthread_cond_init(&o->cv_noel, &at);
```

| Proteção | Espera | Notificação |
|---|---|---|
| nenhuma necessária: ainda não há outras threads | — | — |

- **Ordem obrigatória:** mecanismos e valores iniciais **antes** de qualquer `pthread_create` (`main.c:172` vem antes de `187`). Uma cond var não tem valor inicial a configurar; o "estado inicial" que importa é o das variáveis dos predicados, zeradas pelo `memset`.
- **Criação das threads (`main.c:187-204`):** todas antes de qualquer join. Logo ao nascer, cada uma trava o mutex e entra em `esperar_largada`.
- **Barreira de largada (`main.c:25-31` e `206-213`):** cada thread faz `threads_prontas++` e `broadcast`, e dorme. A main dorme até `threads_prontas == total_threads`, grava `t0`, liga `largada` e faz `broadcast`.

```
main         cria Noel, 9 renas, N elfos ──► lock · espera threads_prontas == 10+N
thread k     lock · threads_prontas++ · broadcast · wait(cv_largada) [solta o mutex]
última       threads_prontas == total · broadcast ──► acorda a main
main         t0 = agora · largada = 1 · broadcast · unlock
todas        acordam, readquirem o mutex uma a uma, veem largada == 1
```

**Se estiver errado:** com `signal` em `main.c:28`, o aviso poderia acordar outra thread trabalhadora em vez da main, e a main dormiria para sempre (essa espera não tem prazo). Com `t0` gravado antes de todas estarem prontas, as chegadas "em 10 ms" incluiriam o tempo de criação das threads.

### 4.2 Chegada dos elfos

```c
// elfo.c:21-32
pthread_mutex_lock(&o->mutex);
esperar_largada(o);
pthread_mutex_unlock(&o->mutex);
dormir_ate_ms(o, o->cfg->elfo0_ms + id);   // SEM o mutex: simula a chegada
pthread_mutex_lock(&o->mutex);             // seção crítica da inscrição
if (o->abortar) { pthread_mutex_unlock(&o->mutex); return NULL; }
o->t_pedido[id] = ms_desde_inicio(o);
```

| Proteção | Espera | Notificação |
|---|---|---|
| inscrição inteira (`elfo.c:27-59`) | o sleep não é espera por condição: é simulação de tempo | nenhuma, até o 3º elfo |

- O sleep é feito **sem o mutex**: outros elfos, renas e Noel continuam funcionando.
- Um elfo que acorda depois do timeout vê `abortar` e sai sem se inscrever (`elfo.c:28-31`).

**Se estiver errado:** dormir com o mutex travaria o programa inteiro durante a chegada.

### 4.3 Formação de um grupo de três elfos

```c
// elfo.c:34-54 — tudo dentro da MESMA seção crítica
int g = o->grupo_aberto;
Grupo *gr = &o->grupos[g];
...
gr->membros[gr->n++] = id;
if (gr->n == TAM_GRUPO) {
    gr->estado = GRUPO_PRONTO;
    o->grupos_fechados++;                       // agora Noel enxerga o grupo
    if (o->grupo_aberto + 1 < o->n_grupos)
        o->grupo_aberto++;                      // o 4º elfo já cai no próximo grupo
    pthread_cond_signal(&o->cv_noel);           // NOTIFICAÇÃO
}
while (gr->estado != GRUPO_CONCLUIDO && !o->abortar)
    pthread_cond_wait(&o->cv_elfos, &o->mutex); // ESPERA
```

| Proteção | Espera | Notificação |
|---|---|---|
| inscrição + fechamento + avanço de `grupo_aberto` numa **única** seção crítica | cada elfo, em `cv_elfos`, pelo **seu** grupo `CONCLUIDO` | o 3º elfo: `signal(cv_noel)` |

Linha do tempo (rodada oficial E06_R10_rep1; tabela completa em [[Lógica e Fluxo (Papai Noel)#Elfos: exemplo passo a passo da formação de grupos]]):

```
10,080  elfo 0 → grupos[0].n = 1, espera em cv_elfos
11,070  elfo 1 → grupos[0].n = 2, espera
12,072  elfo 2 → n = 3 · PRONTO · grupos_fechados = 1 · grupo_aberto = 1 · signal(cv_noel)
13,0xx  elfo 3 → entra em grupos[1] (o grupo 0 já não é o aberto)
```

**Se estiver errado:** avançar `grupo_aberto` numa seção crítica separada abriria uma janela para o 4º elfo entrar num grupo cheio (invasão). Usar `if` no lugar do `while` faria o elfo ir embora no broadcast de outro grupo. A explicação de por que `cv_elfos` usa `broadcast` está em [[Sincronização no Código (Papai Noel)]].

### 4.4 Chegada das renas

```c
// rena.c:21-37
dormir_ate_ms(o, o->cfg->renas_ms);          // as 9 acordam no MESMO instante
pthread_mutex_lock(&o->mutex);               // e disputam o mutex
...
o->renas_prontas++;
if (o->renas_prontas == NUM_RENAS) {
    o->t_nona = ms_desde_inicio(o);
    pthread_cond_signal(&o->cv_noel);        // só a 9ª avisa
}
while (!o->viagem_concluida && !o->abortar)
    pthread_cond_wait(&o->cv_renas, &o->mutex);
```

| Proteção | Espera | Notificação |
|---|---|---|
| `renas_prontas++` (leitura-soma-escrita) | cada rena, em `cv_renas`, por `viagem_concluida` | a 9ª rena: `signal(cv_noel)` |

As 9 renas e, conforme o cenário, alguns elfos acordam quase juntos e entram no mutex **um de cada vez**, numa ordem decidida pelo escalonador. "9ª rena" é **a nona a conseguir o mutex**, não uma rena específica: o id varia entre execuções (rena 8, 1, 2 e 9 nas execuções de verificação).

**Se estiver errado:** sem o mutex, duas renas poderiam ler 7 e gravar 8; o contador nunca chegaria a 9 e a execução terminaria em `timeout`.

### 4.5 A decisão de Noel

```c
// noel.c:86-132 (trechos)
for (;;) {
    if (o->viagem_concluida && o->grupos_concluidos == o->n_grupos) break;   // ENCERRAMENTO
    int renas_ok = o->renas_prontas == NUM_RENAS && !o->viagem_iniciada;  // retrato do estado
    int elfos_ok = o->proximo_grupo < o->grupos_fechados;                 // (com o mutex)
    ...
    if (!liberado || (!renas_ok && !elfos_ok)) {
        int rc = pthread_cond_timedwait(&o->cv_noel, &o->mutex, &limite); // ESPERA
        if (rc == ETIMEDOUT) { o->abortar = 1; ...; break; }
        continue;                                                         // reavalia
    }
    int escolhe_renas = c->ingenua ? !elfos_ok : renas_ok;                // PRIORIDADE
    if (escolhe_renas) preparar_viagem(o);
    else               ajudar_grupo(o, o->proximo_grupo++);               // FIFO
}
```

| Proteção | Espera | Notificação | Prioridade |
|---|---|---|---|
| leitura dos predicados **e** decisão na mesma seção crítica | `timedwait` em `cv_noel`, com prazo `t0 + timeout_ms` | recebida de `rena.c:33` / `elfo.c:53` | `escolhe_renas = renas_ok` |

Por que a decisão é segura:

1. **Leitura e ação atômicas em relação às outras threads.** Entre ler `renas_ok` e marcar `viagem_iniciada = 1` (`noel.c:24`), Noel não solta o mutex. Nenhuma rena ou elfo muda o estado no meio.
2. **`continue` depois de toda espera.** Noel nunca age com base no aviso: volta ao topo e relê o estado. Isso cobre o despertar espúrio, dois avisos virando um só, e o estado que mudou de novo antes de Noel readquirir o mutex.
3. **Prioridade como regra.** Se as duas demandas estão prontas no retrato, a viagem vence. Uma rena que ainda está **bloqueada no `lock`** não faz parte do retrato, e escolher elfos nesse caso **não é violação** (seção 5.5).

### 4.6 Execução de uma ajuda já iniciada

```c
// noel.c:51-73 (trechos)
gr->estado = GRUPO_EM_AJUDA;              // marcado ANTES de soltar o mutex
o->estado = NOEL_AJUDANDO;
o->t_inicio_ajuda[...] = gr->t_inicio;
pthread_mutex_unlock(&o->mutex);          // libera o estado para os outros
dormir_ate_ms(o, inicio + o->cfg->ajuda_ms);   // NÃO olha nada durante a ajuda
pthread_mutex_lock(&o->mutex);
gr->estado = GRUPO_CONCLUIDO;
o->grupos_concluidos++;
pthread_cond_broadcast(&o->cv_elfos);     // libera os 3 elfos do grupo
```

| Proteção | Espera | Notificação |
|---|---|---|
| marcação do início e da conclusão | — (Noel está num sleep, não numa cond var) | `broadcast(cv_elfos)` no fim |

**A não interrupção** vem da estrutura, não de um mecanismo: (1) **só a thread Noel decide** e (2) durante a ajuda ela está dormindo, fora de `cv_noel`. A 9ª rena pode chegar, incrementar o contador e dar `signal`, mas ninguém está ouvindo. O aviso se perde e o estado fica. Noel só reavalia ao voltar ao topo do laço (cenário 5.4).

**Se estiver errado:** se `EM_AJUDA` só fosse marcado depois do sleep, nada impediria que outra decisão pegasse o mesmo grupo. Neste código isso só não aconteceria porque `proximo_grupo++` já avançou, o que seria uma proteção acidental. Se Noel esperasse a ajuda em `cv_noel` com timeout de 3 ms, em vez de dormir, a 9ª rena o "acordaria no meio", e seria preciso decidir o que fazer com a ajuda interrompida.

### 4.7 Preparação da viagem

Mesma estrutura de 4.6, em `preparar_viagem` (`noel.c:19-42`): `viagem_iniciada = 1` com o mutex, `unlock`, sleep de `preparo_ms`, `lock`, `viagem_concluida = 1`, `broadcast(cv_renas)`. As 9 renas acordam, readquirem o mutex uma a uma, veem `viagem_concluida == 1` e saem. `viagem_iniciada` impede uma segunda viagem (`noel.c:89`); `viagem_concluida` libera as renas e entra na condição de término.

Durante a preparação, grupos podem ficar prontos e entrar na fila. O `signal` do 3º elfo também se perde, mas `grupos_fechados` fica gravado.

### 4.8 Atendimento dos grupos restantes

Não há código especial: o mesmo laço continua. Depois da viagem, `renas_ok` é sempre 0 (`viagem_iniciada == 1`), e cada volta ao topo encontra `elfos_ok = 1` enquanto houver grupo fechado não atendido. Noel encadeia as ajudas **sem dormir em `cv_noel`**, em ordem FIFO (`proximo_grupo++`). Se o próximo grupo ainda não estiver completo, Noel dorme até o `signal` do 3º elfo.

Exemplo (rodada oficial, E06_R10_rep1): fim da viagem em 15,185 ms → grupo 1 em 15,200 → fim em 18,271 → grupo 2 em 18,279 → fim em 21,358.

### 4.9 Encerramento das threads

```c
// noel.c:86-87 e 135-145
if (o->viagem_concluida && o->grupos_concluidos == o->n_grupos) break;
...
pthread_cond_broadcast(&o->cv_elfos);    // ninguém pode ficar bloqueado
pthread_cond_broadcast(&o->cv_renas);
pthread_mutex_unlock(&o->mutex);
```

| Caminho | O que garante o término de cada thread |
|---|---|
| **Normal** | cada elfo foi liberado pelo broadcast do fim do seu grupo; as renas, pelo do fim da viagem. Noel sai pelo `break`. Os broadcasts finais são redundantes (rede de segurança) |
| **Timeout** | `abortar = 1`; os broadcasts finais acordam quem espera em `cv_elfos`/`cv_renas` (predicados com `!abortar`); quem ainda está no sleep de chegada acorda depois, vê `abortar` e sai sem se inscrever |
| **main** | `pthread_join` de todas (`main.c:215-219`); só então `destruir_oficina` (`main.c:222`) e o cálculo das métricas |

Limites verificados [CONFIRMADO 2026-10-28]:
- O timeout só é verificado quando Noel espera **sem trabalho**: não é um limite de duração total (T = 215 ms com `--ajuda-ms 100 --timeout-ms 50`, status `ok`).
- Ele não interrompe sleeps: com renas em 3000 ms, o status foi `timeout` em T = 2000 ms, mas o processo durou 3,0 s, até as renas acordarem e verem `abortar`.
- Ele não protege contra um mutex nunca liberado, nem contra a espera da main na largada, que não tem prazo ([[Riscos de Sincronização (Papai Noel)#4. Esperas que nunca terminam]]).

## 5. Cenários

O 1º grupo fica pronto em ≈ 12 ms (elfo 2 chega em 10 + 2) e o 2º em ≈ 15 ms. A ajuda dura 3 ms e a preparação, 5 ms (padrões). "Antes", "junto" e "depois" são relativos a isso.

### 5.1 Renas **antes** dos elfos (`--renas-ms 5`), verificação

```
 5,093  9ª rena → signal                      Noel dormindo
 5,111  DECISÃO: viagem (só renas_ok)         preparando
10,074  elfo 0 chega (Noel preparando)
10,170  fim da preparação · broadcast(cv_renas)
12,078  grupo 1 PRONTO → 12,103 ajuda 1       (Noel livre: espera ≈ 0)
15,066  grupo 2 PRONTO (Noel ajudando o grupo 1)
15,174  fim da ajuda 1 → 15,182 ajuda 2       (sem dormir: elfos_ok já era 1)
18,264  encerramento
```

**Garante:** a viagem acontece antes dos elfos simplesmente porque é a única demanda. Não há disputa (`decisoes_com_disputa = 0`). **Depende do escalonador:** nada relevante; os tempos variam em µs.

### 5.2 Renas **junto** dos elfos (`--renas-ms 10`), rodada oficial

Linha do tempo completa em [[Lógica e Fluxo (Papai Noel)#Linhas do tempo reais (6 elfos)]]. Resumo: o elfo 0 e as 9 renas acordam em ~10 ms e disputam o mutex. Noel decide pela viagem em 10,108 ms, quando **só** as renas estão prontas (o grupo 1 só fecha em ~12 ms). Os dois grupos ficam prontos **durante** a preparação e esperam na fila; depois são atendidos em sequência.

**Garante:** a preparação não é interrompida pelos grupos que ficam prontos. **Depende do escalonador:** a ordem elfo 0 × 9ª rena no mutex (o elfo 0 entrou antes, em 10,080 contra 10,091 ms). Isso não muda a decisão, porque o elfo 0 sozinho não forma grupo. É o cenário com **maior espera dos elfos** (p95 ≈ 5,2 ms): o custo visível da prioridade.

### 5.3 Renas **depois** dos elfos (`--renas-ms 30`), rodada oficial

Os grupos ficam prontos em ~12 e ~15 ms com Noel livre, e são atendidos de imediato. A 9ª rena chega em ~30,1 ms, com Noel dormindo; a decisão pela viagem sai ~45 µs depois. **Garante:** nenhum elfo espera pelas renas. **Depende do escalonador:** nada relevante.

### 5.4 Renas chegando **enquanto Noel ajuda** três elfos (`--renas-ms 13`), verificação

```
12,070  elfo 2 → grupo 1 PRONTO · signal(cv_noel)
12,096  DECISÃO: grupo 1 (só elfos_ok)       ajudando  ── Noel solta o mutex e dorme 3 ms
13,081  elfo 3 chega (grupo 2)               ajudando
13,095  9ª RENA → signal(cv_noel)            ajudando  ← ninguém ouve: Noel não está em cv_noel
15,073  elfo 5 → grupo 2 PRONTO · signal     ajudando  ← também se perde
15,172  fim da ajuda 1 · broadcast(cv_elfos) dormindo
15,180  DECISÃO: viagem                      preparando ← renas_ok E elfos_ok: disputa → renas
20,255  fim da preparação · broadcast(cv_renas)
20,271  DECISÃO: grupo 2 → 23,310 fim
23,313  encerramento
```

**Garante:** (1) a ajuda ao grupo 1 **não é interrompida**: a rena chega em 13,095 e Noel só reage em 15,180, depois de terminar; (2) na volta ao topo, as **duas** demandas estão prontas, e a viagem vence: o grupo 2, pronto desde 15,073, espera mais 5 ms. **Por que funciona sem o aviso:** os dois `signal` se perderam, mas `renas_prontas == 9` e `grupos_fechados == 2` estavam gravados, e Noel os releu em `noel.c:89-90` antes de pensar em dormir. **Depende do escalonador:** nada que altere a ordem das decisões.

### 5.5 **Ambos os grupos prontos** antes da decisão de Noel

**(a) Forçado: `--teste-prioridade --renas-ms 30`, verificação**

```
12,078  grupo 1 PRONTO  ─┐ Noel NÃO é liberado: só elfos_ok (noel.c:94-98)
15,077  grupo 2 PRONTO  ─┘ continua em timedwait (sem sleep)
30,160  9ª rena → signal
30,202  DECISÃO (disputa: renas_ok e elfos_ok) → viagem
35,314  grupo 1 → 38,447 grupo 2 → 41,530 encerramento      RESULTADO: PASSOU, código 0
```

Com `--ingenua` no mesmo cenário (verificação): 30,267 grupo 1 → 33,791 grupo 2 → 36,899 viagem. São **2 violações** (as duas decisões por elfos com as renas prontas), resposta às renas de 6,7 ms, `RESULTADO: FALHOU`, código 1. Os mecanismos são os mesmos; só a regra de `noel.c:117` mudou.

**(b) Natural: `--renas-ms 12` (renas e 3º elfo no mesmo instante), 30 execuções de verificação**

| 1ª decisão | Execuções | Exemplo | Por quê |
|---|---|---|---|
| **viagem** | 8/30 | rep 1: 9ª rena 12,079 → grupo 1 pronto 12,092 → decisão 12,099 = viagem | as duas demandas estavam no retrato: **disputa**, renas vencem |
| **grupo 1** | 22/30 | rep 10: grupo 1 pronto 12,080 → decisão 12,114 = grupo 1 → 9ª rena **12,117** | quando Noel decidiu, a 9ª rena ainda **não tinha conseguido o mutex**: para o programa, ela não tinha chegado |

Nas 30 execuções: **0 violações** e status `ok`. Nas 22 em que o grupo 1 foi primeiro, a disputa aconteceu na decisão seguinte (fim da ajuda 1, ~15,2 ms, com renas e grupo 2 prontos), e a viagem venceu.

**O que isso mostra:** a implementação garante a prioridade **sobre o estado registrado**. Quem "chegou primeiro" é decidido por quem adquiriu o mutex primeiro, e isso é do escalonador. A rena acorda do sleep às 12,000 ms, mas fica na fila do mutex atrás de outras renas e do elfo; o instante gravado (`t_nona`) é o da entrada na seção crítica. Esse é o ponto sutil descrito em [[Lógica e Fluxo (Papai Noel)#O que deve acontecer em cada cenário]].

## 6. O que é garantido e o que não é

| Afirmação | Base | Status |
|---|---|---|
| Nenhum grupo é atendido com ≠ 3 elfos; nenhum elfo invade grupo fechado | inscrição, fechamento e avanço de `grupo_aberto` na mesma seção crítica | garantido por construção (análise do código) |
| A viagem só começa com 9 renas e acontece uma vez | `renas_ok` (`noel.c:89`) | garantido por construção |
| Com as duas demandas no retrato, a viagem vence | `noel.c:117` | garantido por construção; testado (`--teste-prioridade` PASSOU) |
| Uma tarefa iniciada não é interrompida | só Noel decide e ele não decide durante a tarefa | garantido por construção |
| Todos terminam (normal ou timeout) | broadcasts por tarefa e finais; `abortar` nos predicados | garantido por construção; estresse 300/300 `ok` |
| Qual demanda é vista primeiro num empate de chegada | ordem de aquisição do mutex | **depende do escalonador** (8/30 × 22/30 no cenário 5.5b) |
| Ordem das renas entre si e id da "9ª rena" | ordem de aquisição do mutex | **depende do escalonador** |
| Ausência de corridas de dados | inspeção do código | **não verificada por ferramenta** (TSan e Helgrind indisponíveis) |
| Robustez a falhas de `pthread_*_init` e `pthread_create` | retornos não verificados / sem join no erro | **defeito conhecido** ([[Riscos de Sincronização (Papai Noel)]]) |

> Execuções sem violação mostram que as regras valeram **nas execuções observadas**. A garantia vem do raciocínio sobre o código; os testes só podem mostrar a presença de erros.

## 7. Os blocos que você precisa dominar para a apresentação

1. **Inicialização** (`main.c:131-140`): 1 mutex com atributos padrão; 4 cond vars, sendo `cv_noel` com `CLOCK_MONOTONIC` para o timeout. Os valores iniciais que importam são os dos **predicados**, zerados pelo `memset` (`main.c:109`). Não há semáforos.
2. **Fechamento do grupo** (`elfo.c:41-53`): inscrição + `PRONTO` + `grupos_fechados++` + `grupo_aberto++` + `signal`, tudo numa seção crítica. É o que impede a invasão.
3. **9ª rena** (`rena.c:28-33`): `renas_prontas++` protegido pelo mutex, e só a nona avisa Noel.
4. **Laço de Noel** (`noel.c:86-108`): término no topo, predicados lidos com o mutex, `timedwait` + `continue`. Saiba explicar por que um aviso perdido não é bug.
5. **Prioridade** (`noel.c:117`): `escolhe_renas = renas_ok`. Compare com `--ingenua`: os mesmos mecanismos, a regra invertida e 2 violações.
6. **Tarefa sem interrupção** (`noel.c:31-33`, `60-62`): marca o início com o mutex, solta, dorme, retrava, conclui e faz `broadcast`. Explique por que é `broadcast` (`cv_elfos` tem elfos de vários grupos; `cv_renas` tem 9 renas).
7. **Encerramento** (`noel.c:135-145` + `main.c:215-222`): broadcasts finais, `abortar`, joins e só então destroy.

Perguntas da banca com respostas prontas: [[Perguntas da Apresentação (Papai Noel)]].
