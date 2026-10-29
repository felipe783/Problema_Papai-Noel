# Interpretação dos Gráficos (Papai Noel)

Como **ler, interpretar e defender** cada gráfico do trabalho. O objetivo é olhar para qualquer um deles e saber justificar a conclusão, não decorar o slide. Os números estão resumidos em [[Testes e Gráficos (Papai Noel)]]; esta nota explica **o porquê** de cada um. A fala slide a slide está em [[Guia da Apresentação v4 (Papai Noel)]] (slides 16–18 e 21–26). Índice: [[_Papai-Noel]].

> Fontes, todas conferidas em 2026-10-28 [CONFIRMADO 2026-10-28]: `tema11_papai_noel/graficos/G1–G4.png`, `scripts/graficos.py` (gera os PNGs só a partir dos CSVs), `dados/resumo.csv`, `dados/espera_elfos.csv`, `dados/eventos.csv`, `dados/tabela_esperas.csv`, `dados/teste_prioridade/`, `dados/ingenua/`, `apresentacao/gerar_apresentacao.py` e `src/`. Os PNGs ficam fora do vault: abra-os pelo explorador ou pelos slides 22–25.

## Sumário

1. Inventário: que tipo de gráfico é cada um
2. O cenário por trás de todos os gráficos (leia antes)
3. Método de leitura em 7 passos
4. G1: vazão × nº de elfos
5. G2: chegada das renas × espera dos elfos e resposta às renas
6. G3: espera por grupo na referência
7. G4: linha do tempo do Noel
8. As linhas do tempo dos slides 16, 17 e 18 e as barras do slide 31
9. Perguntas transversais do professor
10. Melhorias sugeridas para os gráficos
11. Exercícios (responda antes de abrir a resposta)

---

## 1. Inventário: que tipo de gráfico é cada um

Antes de explicar um gráfico, diga **de onde ele vem**. Um professor que pergunta "isso foi medido?" quer saber exatamente isso.

| Onde | Gráfico | Tipo | Origem dos dados |
|---|---|---|---|
| Slide 22 | **G1** vazão × elfos | **Execução real, matriz oficial** | `resumo.csv`, 15 execuções (3 configurações × 5) |
| Slide 23 | **G2** p95 × chegada das renas + resposta às renas | **Execução real, matriz oficial** | `resumo.csv`, 15 execuções (3 × 5) |
| Slide 24 | **G3** espera por grupo | **Execução real, matriz oficial** | `espera_elfos.csv`, 5 execuções de `E06_R10` |
| Slide 25 | **G4** linha do tempo do Noel | **Execução real, uma execução** | `eventos.csv`, só `E06_R10_rep1` |
| Slide 17 | 3 linhas do tempo (antes/junto/depois) | **Execução real, matriz oficial** | `eventos.csv`, repetição 1 de `E06_R05`, `E06_R10`, `E06_R30` |
| Slide 18 | correta × ingênua | **Execução real, teste dedicado** | `dados/teste_prioridade/` e `dados/ingenua/` |
| Slide 16 | rena chega durante a ajuda | **Execução real fora da matriz, sem dados salvos** | valores digitados em `gerar_apresentacao.py` (`R13`), de `--renas-ms 13` |
| Slide 31 | barras 12/30 × 18/30 (empate) | **Execução real fora da matriz, sem dados salvos** | valores digitados (`EMPATE`), de 30 × `--renas-ms 12` |
| Slide 4 | tabelas "sem mutex × com mutex" | **Hipotético** (entrelaçamento possível, não medido) | raciocínio; o programa nunca roda sem mutex |
| Slides 6, 9, 12, 14, 15 | fluxos, raias, fluxograma | **Conceitual** (estrutura do código, sem tempo medido) | código de `src/` |

**O que falta de contexto (lacunas reais):**
- Slides 16 e 31: os números vêm de execuções avulsas cujo CSV não foi guardado em `dados/`. Reexecutei os dois cenários em 2026-10-28 (fora do projeto): a **ordem** dos eventos se repetiu no slide 16, mas com tempos alguns µs diferentes; no slide 31, a proporção deu **10/30 viagem** (o slide diz 12/30, e outra nota do vault registra 8/30). A proporção varia de rodada para rodada; o que não muda é zero violações. Sugestão na seção 10.
- Nenhum PNG mostra **utilização do Noel**, nem o teste de prioridade como gráfico de barras; estão só em tabela e no slide 18.
- O enunciado do trabalho não está no vault, então "o professor pediu 5 repetições" é [NÃO VERIFICADO].

---

## 2. O cenário por trás de todos os gráficos (leia antes)

Quase tudo nos gráficos se explica por uma coisa: **o cenário é dirigido pelo relógio**. Não há aleatoriedade (`--semente` só identifica a repetição). Os horários vêm dos parâmetros padrão de `main.c:77-78`:

| Evento | Quando | Onde no código |
|---|---|---|
| Elfo `i` chega | `elfo0_ms + i` = **10 + i ms** (elfo 0 em 10, elfo 1 em 11...) | `elfo.c:25` |
| As 9 renas chegam | todas em `renas_ms` (5, 10 ou 30 ms) | `rena.c:21` |
| Ajuda a um grupo | dura **3 ms** (`ajuda_ms`) | `noel.c:61` |
| Preparação da viagem | dura **5 ms** (`preparo_ms`) | `noel.c:32` |
| Grupo k fica pronto | quando chega o 3º elfo: **12, 15, 18... ms** | `elfo.c:45-53` |

Os sleeps só **simulam** durações (`clock_nanosleep` absoluto). Nenhuma coordenação depende deles. A coordenação é feita pelo mutex e pelas 4 variáveis de condição ([[Sincronização no Código (Papai Noel)]]).

**Consequência:** dá para **prever** o resultado no papel, e os gráficos confirmam a previsão com um pequeno atraso (dezenas de µs por passo). Esse atraso é o custo real do SO: acordar uma thread, escalonar e retomar o mutex. Se o gráfico se afastasse muito da previsão, isso indicaria um problema de sincronização (por exemplo, um aviso perdido deixaria o Noel dormindo até o timeout de 2000 ms).

**Onde cada métrica é gravada** (`metricas.c:43-71`):

| Métrica | Fórmula | Momentos gravados em |
|---|---|---|
| T | encerramento do Noel − t0 | `noel.c:137` |
| Vazão | `concluidos / (T/1000)` pedidos/s | `metricas.c:49` |
| Espera do elfo | `t_inicio_ajuda − t_pedido` | `elfo.c:32` (pedido) e `noel.c:56` (início da ajuda) |
| p95 | posição ⌈0,95·n⌉ das esperas ordenadas | `metricas.c:17-27` |
| Resposta às renas | `t_ini_preparo − t_nona` | `rena.c:31` (9ª rena) e `noel.c:27` (início do preparo) |
| Utilização | tempo ocupado / T | `noel.c:36` e `noel.c:65` |

> **Atenção à espera do elfo:** ela inclui o tempo que o elfo passa esperando **os colegas** completarem o grupo, não só o tempo esperando o Noel. O elfo 0 chega em 10 ms e o grupo só fecha em 12 ms: ele espera pelo menos 2 ms mesmo que o Noel esteja livre. Isso explica o "piso" de ~2 ms no G2.

> **Atenção ao p95:** com n = 3 (um grupo) ou n = 6 (uma execução de 6 elfos), ⌈0,95·n⌉ = n, ou seja, **o p95 é o máximo**. Diga isso antes que o professor pergunte.

---

## 3. Método de leitura em 7 passos

Use sempre a mesma sequência, em qualquer gráfico, inclusive num que você nunca viu:

1. **Título e origem.** O que é medido, em qual configuração, quantas execuções? É real, conceitual ou hipotético?
2. **Eixos e unidades.** O que é X (o que variou)? O que é Y (o que foi medido)? Em ms ou µs? O eixo começa em zero?
3. **Elementos.** O que é cada ponto, barra, linha, cor ou hachura? A barra de erro é desvio padrão ou mín–máx? (Aqui é sempre **mín–máx**.)
4. **Tendência.** Sobe, desce, fica igual? Há salto, cruzamento ou ponto fora do padrão?
5. **Magnitude × ruído.** A diferença entre os pontos é maior que a barra de variação? Se não for, não conclua nada.
6. **Mecanismo.** Que regra do problema ou que trecho do código produz isso? Faça a conta do cenário (seção 2) e compare.
7. **Alcance da conclusão.** Separe o que o gráfico **comprova**, o que só **sugere** e o que ele **não pode** dizer.

O passo 7 é o que separa "repetir o slide" de "entender o gráfico". Regra geral deste trabalho: **gráficos de desempenho medem o cenário; a correção da sincronização vem da análise do código e dos contadores de violação**.

---

## 4. G1: vazão × nº de elfos

`graficos/G1_vazao_elfos.png` · slide 22 · gerado em `graficos.py:106-123`.

### Objetivo
Responder "o que acontece com o desempenho quando aumentam as threads de elfos?" (fator A da matriz). Foi criado para testar a hipótese H<sub>A</sub>: a vazão cresce com o número de elfos.

### Elementos
- **Eixo X:** quantidade de elfos (3, 6, 12). É numérico; o espaçamento entre 6 e 12 é o dobro do entre 3 e 6.
- **Eixo Y:** vazão em **pedidos de elfos atendidos por segundo**, começando em 0.
- **Ponto azul:** média das 5 repetições. **Barra de erro:** mín–máx das 5. Ela é **menor que o marcador**, por isso quase não aparece.
- **Linha azul clara:** só guia o olho entre pontos numéricos ordenados; não é uma medida entre os pontos.
- **Rótulos:** 163,4; 280,9; 436,1.
- **Fixo:** renas em 10 ms ("junto").

### Interpretação
- **Tendência:** cresce, mas **cada vez menos** por elfo: dobrar de 3 para 6 elfos dá +72%, e dobrar de 6 para 12, +55%.
- **Mecanismo:** existe um **custo fixo inicial** de ~15 ms (ninguém chega antes de 10 ms, e a viagem ocupa o Noel de 10 a 15 ms). Depois, os grupos ficam prontos a cada 3 ms e cada ajuda dura 3 ms, então o Noel atende um atrás do outro. Conta: **T ≈ 15 + N ms**, logo vazão ≈ N / (15 + N) × 1000.

| Elfos | Previsto (pedidos/s) | Medido | Diferença |
|---|---|---|---|
| 3 | 166,7 | 163,4 | −2% |
| 6 | 285,7 | 280,9 | −2% |
| 12 | 444,4 | 436,1 | −2% |
| 24 (extra) | 615 | 601,2 | −2% |
| 48 (extra) | 762 | 744,2 | −2% |

As linhas 24 e 48 vêm de execuções extras **fora da matriz** (1 execução cada, 2026-10-28) [CONFIRMADO 2026-10-28, fora da matriz]. A curva tende a **1000 pedidos/s** (3 elfos a cada 3 ms), que é a **capacidade do Noel**.
- **Os ~2% abaixo:** cada sleep acorda algumas dezenas de µs depois do instante pedido, e cada passagem do mutex custa alguns µs. Esse atraso se acumula em T.

### Relação com o código e com a sincronização
- A **fila FIFO de grupos** (`grupo_aberto`, `proximo_grupo`, `grupos_fechados` em `elfo.c:34-53` e `noel.c:90, 128`) é o que mantém o Noel ocupado sem buracos: quando ele termina uma ajuda, volta ao topo do laço e já encontra `elfos_ok = 1`, sem precisar dormir.
- **Exclusão mútua:** o Noel é um recurso único e serializado. Mais elfos **não** criam paralelismo de atendimento: ele continua ajudando **um grupo por vez**. O ganho vem só de diluir o custo fixo.
- **Aviso perdido: onde ele apareceria.** Se um `pthread_cond_signal(&o->cv_noel)` (`elfo.c:53`) se perdesse com o Noel dormindo, ele só acordaria no timeout de 2000 ms, e o status seria `timeout`. **Essa execução não apareceria no G1:** `graficos.py:71` usa só as execuções `ok`. O sintoma seria o "n = 5" do título cair e `taxa_validas` < 1 em `tabela_esperas.csv`. Por isso, antes de ler a curva, confira **25/25 `ok`**. Nessas execuções, isso não ocorreu; a razão está no código: o predicado é testado em `while`, com o mutex, antes de dormir.
- **Preempção do SO:** a variação entre repetições (163,4: de 160,0 a 164,3) é o efeito do escalonador do SO, que decide quando cada thread volta a rodar depois do sleep.

### Comprova × sugere × não pode concluir
- **Comprova:** nessas 15 execuções, a vazão cresce com N, e a diferença entre configurações (> 100 pedidos/s) é muito maior que a variação (< 5 pedidos/s). H<sub>A</sub> foi confirmada.
- **Sugere:** a vazão satura perto de 1000/s (apoiado pelas execuções extras com 24 e 48 elfos).
- **Não pode concluir:** que a sincronização é eficiente ou correta. A vazão é quase toda **ditada pelo cenário** (horários fixos); uma solução errada (a ingênua) teria vazão parecida. Também não diz nada sobre multicore ou paralelismo.

### Perguntas do professor
- *"O que esse gráfico mostra?"* A vazão de pedidos de elfos atendidos por segundo, com 3, 6 e 12 elfos e as renas fixas em 10 ms; cada ponto é a média de 5 execuções.
- *"Como chegou a essa conclusão?"* Pela conta do cenário (T ≈ 15 + N), que bate com o medido a 2%, e porque a diferença entre os pontos é muito maior que a barra mín–máx.
- *"Com mais threads, o que muda?"* A vazão continua subindo, cada vez menos, até perto de 1000/s. Medi 601/s com 24 elfos e 744/s com 48. A utilização do Noel sobe (45% → 63% → 84% com 48), porque o tempo ocioso inicial fica pequeno perto do tempo atendendo.
- *"Mais elfos = mais rápido porque roda em paralelo?"* Não. O Noel atende um grupo por vez. Os elfos passam quase todo o tempo dormindo (sleep ou `cond_wait`), sem disputar CPU.

### Roteiro oral
🎤 "No G1, as renas ficam fixas em 10 milissegundos e o que varia é a quantidade de elfos, no eixo X. No eixo Y está a vazão: quantos pedidos de elfos o Noel atende por segundo. Cada ponto é a média de cinco execuções, e a variação entre elas é tão pequena que a barra some atrás do ponto. A vazão sobe de 163 para 281 e para 436. O motivo é um custo fixo: ninguém chega antes de 10 milissegundos, e o Noel gasta 5 com a viagem. Depois disso, ele atende um grupo a cada 3 milissegundos, sem pausa. Quanto mais elfos, mais esse custo inicial se dilui. A conta 'quinze mais N' prevê esses valores com 2% de diferença. O ganho não vem de paralelismo: o Noel continua atendendo um grupo por vez."

---

## 5. G2: chegada das renas × espera dos elfos e resposta às renas

`graficos/G2_p95_renas.png` · slide 23 · gerado em `graficos.py:125-158`.

### Objetivo
Mostrar o **custo da prioridade às renas**: quem espera mais quando as renas chegam antes, junto ou depois dos elfos (fator B). Hipótese H<sub>B</sub>: o horário das renas muda a espera dos elfos.

### Elementos
- **Dois painéis com unidades diferentes:** o esquerdo em **ms**, o direito em **µs** (1 ms = 1000 µs). É o erro de leitura mais fácil de cometer.
- **Eixo X (os dois):** chegada das 9 renas: antes (5 ms), junto (10 ms), depois (30 ms). São **categorias**, por isso os pontos não são ligados por linha.
- **Esquerdo, Y:** p95 da espera dos elfos (com 6 elfos, o p95 é o **máximo** da execução). **Ponto laranja:** média dos 5 p95; **barra:** mín–máx (invisível de tão pequena).
- **Direito, Y:** resposta às renas = da chegada da 9ª rena ao início da preparação. **Ponto roxo:** média de 5; **barra:** mín–máx.
- **Fixo:** 6 elfos.

### Interpretação
**Painel esquerdo: 2,10 / 5,20 / 2,11 ms.** Só "junto" é diferente. Siga a linha do tempo de cada caso:

| Caso | O Noel quando o grupo 1 fecha (12 ms) | Quem espera o quê | Espera do elfo 0 |
|---|---|---|---|
| Antes (5 ms) | livre (a viagem foi de 5 a 10 ms) | só os colegas | 12 − 10 ≈ **2 ms** |
| Junto (10 ms) | **preparando a viagem** (10 a 15 ms) | os colegas **e a viagem** | 15,2 − 10,08 ≈ **5,1 ms** |
| Depois (30 ms) | livre (renas ainda não chegaram) | só os colegas | 12 − 10 ≈ **2 ms** |

O valor de 2 ms **não é espera pelo Noel**: é o elfo 0 esperando os elfos 1 e 2 chegarem (em 11 e 12 ms). Na execução `E06_R05_rep1`, o elfo 2, o último do grupo, espera só **0,025 ms**, que é o tempo do Noel acordar e começar quando está livre [CONFIRMADO 2026-10-28, `espera_elfos.csv`].

**Painel direito: ~20, 18 e 21 µs, com faixas de 8 a 45 µs.** As três faixas se sobrepõem: **não há diferença real entre os casos**. Em todos, a 9ª rena encontra o Noel **dormindo** em `cond_timedwait` (`noel.c:101`), então o tempo é só acordar: o `pthread_cond_signal` (`rena.c:33`), o escalonador colocando o Noel para rodar, a retomada do mutex e a gravação de `t_ini_preparo` (`noel.c:27`). A dispersão (8 a 45 µs) é o ruído do escalonador do SO.

### Relação com o código e com a sincronização
- **Prioridade não preemptiva:** no caso "junto", o grupo 1 fecha durante a viagem. O `signal` em `cv_noel` não interrompe nada: o Noel está dormindo em `dormir_ate_ms` (`noel.c:32`), **sem o mutex**, e só reavalia no topo do laço. O grupo espera a viagem acabar. É o "preço da prioridade" pago pelos elfos.
- **Espera eficiente (sem espera ocupada):** a resposta de µs mostra que o Noel acorda **logo** que a condição fica verdadeira. Se ele verificasse por polling (por exemplo, a cada 1 ms), a resposta seria da ordem do período de polling.
- **Seção crítica:** a 9ª rena incrementa `renas_prontas` e sinaliza dentro do mutex (`rena.c:23-33`). Isso garante que o Noel, ao retomar o mutex, **vê** `renas_prontas == 9`.

### Comprova × sugere × não pode concluir
- **Comprova:** com as renas "junto", a espera máxima dos elfos sobe ~3 ms, uma diferença 30 vezes maior que a variação (< 0,1 ms). E as renas foram atendidas em µs nos três cenários. H<sub>B</sub> confirmada.
- **Sugere:** que a espera extra dos elfos é igual à sobreposição entre a viagem e a formação do grupo (15,2 − 12,07 ≈ 3,1 ms), pela conta do cenário.
- **Não pode concluir:**
  - **que a prioridade às renas funciona numa disputa.** Na matriz, nenhuma decisão teve as duas demandas prontas ao mesmo tempo (`com disputa: 0` em `dados/log_execucao.txt`). O painel direito mede a latência de acordar, não a regra de prioridade. Quem testa a prioridade é o slide 18;
  - que um cenário é "mais rápido" para as renas que outro: as faixas se sobrepõem.

### Perguntas do professor
- *"Por que os pontos não estão ligados?"* Porque X são categorias (antes/junto/depois), não uma escala contínua: ligar sugeriria valores intermediários que não existem.
- *"O painel direito tem barras enormes. A medida é ruim?"* Estão em µs: de 8 a 45 µs. É ruído do escalonador, 100 vezes menor que a preparação de 5 ms.
- *"Esse gráfico prova a prioridade?"* Não. Prova o custo dela no caso "junto". Na matriz nunca houve disputa; a prioridade é exercitada pelo `--teste-prioridade` e comparada com a `--ingenua` (slide 18).
- *"Por que antes e depois dão o mesmo valor, se são tão diferentes?"* Nos dois, o Noel está livre quando cada grupo fecha. Para os elfos, não importa se a viagem foi antes ou será depois: o que importa é se ela coincide com a formação do grupo.

### Roteiro oral
🎤 "O G2 tem dois painéis, e cuidado com as unidades: o da esquerda está em milissegundos e o da direita em microssegundos. Fixamos 6 elfos e mudamos só o horário das renas. À esquerda, a maior espera dos elfos: 2,1 milissegundos com as renas antes ou depois, e 5,2 quando chegam junto. Esses 2,1 são o primeiro elfo esperando os colegas formarem o grupo. No caso 'junto', o grupo fecha enquanto o Noel prepara a viagem, e espera ela acabar, porque a preparação não é interrompida. É o preço da prioridade. À direita, a resposta às renas: uns 20 microssegundos em qualquer caso, que é o tempo de acordar o Noel pela variável de condição. As faixas se sobrepõem, então não há diferença entre os cenários. Um cuidado: esse gráfico mostra o custo da prioridade, não a prioridade numa disputa. Isso está no slide 18."

---

## 6. G3: espera por grupo na referência

`graficos/G3_p95_grupo.png` · slide 24 · gerado em `graficos.py:160-184`.

### Objetivo
Verificar se o **grupo atendido depois espera mais** (atraso acumulando na fila). Expectativa intuitiva: o grupo 2 espera mais que o grupo 1.

### Elementos
- **Eixo X:** grupo 1 e grupo 2, na ordem de atendimento. **Eixo Y:** p95 da espera dos 3 membros, em ms. Como cada grupo tem 3 elfos, **é a maior espera do grupo**.
- **Ponto verde:** média dos 5 p95 (um por execução); **barra:** mín–máx.
- **Pontos cinza, deslocados à direita:** o p95 de cada uma das 5 execuções (mostram a dispersão real).
- **Anotação:** "5 execuções × 3 elfos (n = 15 amostras)".
- **Fixo:** referência (6 elfos, renas em 10 ms).

### Interpretação
- **Resultado:** grupo 1 = **5,12 ms** (5,10–5,18); grupo 2 = **5,20 ms** (5,17–5,25). Praticamente iguais. **A expectativa não se confirmou.**
- **Mecanismo:**
  - O grupo 1 fica pronto em 12,07 e espera o fim da **viagem** (15,2). O elfo 0, que chegou em 10,08, espera 5,12.
  - O grupo 2 fica pronto em 15,06 e espera o fim da **ajuda ao grupo 1** (18,28). O elfo 3, que chegou em 13,07, espera 5,21.
  - Os grupos chegam **a cada 3 ms** e cada ajuda dura **3 ms**: a taxa de chegada é igual à taxa de atendimento. O atraso inicial (a viagem) **é passado adiante, sem crescer**.
- **E os 0,08 ms a mais do grupo 2?** É o pequeno atraso por ciclo: a ajuda começa alguns µs depois da decisão e o sleep acorda um pouco depois do pedido, então cada ciclo dura ~3,07 ms, não 3,00. Isso aparece de forma consistente: nas 5 execuções, o grupo 2 está 0,07 a 0,09 ms acima do grupo 1 [CONFIRMADO 2026-10-28, `espera_elfos.csv`].

### Teste de sensibilidade (fora da matriz)
Para mostrar que o raciocínio está certo, rodei 12 elfos com a ajuda durando **4 ms** (mais lenta que a chegada dos grupos) [CONFIRMADO 2026-10-28, 1 execução fora da matriz]:

| Grupo | Maior espera com ajuda de 3 ms (E12_R10) | Maior espera com ajuda de 4 ms |
|---|---|---|
| 1 | ~5,1 | 5,10 |
| 2 | ~5,2 | 6,25 |
| 3 | ~5,3 | 7,34 |
| 4 | ~5,4 | 8,43 |

Com 4 ms, cada grupo espera **~1,1 ms a mais** que o anterior: a fila cresce, porque o atendimento (4 ms) é mais lento que a chegada (3 ms). Com 3 ms, ela fica estável. É a lógica de fila de um escalonador: se a taxa de chegada passa a de serviço, a espera cresce sem limite.

### Relação com o código e com a sincronização
- **FIFO:** `proximo_grupo++` (`noel.c:128`) atende os grupos na ordem em que fecharam. Nenhum grupo "fura" a fila, o que mantém a espera previsível.
- **Grupo isolado:** o 3º elfo fecha o grupo e avança `grupo_aberto` na mesma seção crítica (`elfo.c:45-53`). Por isso todo grupo tem exatamente 3 elfos e o p95 tem sempre 3 amostras.
- **Broadcast por grupo:** ao fim da ajuda, `pthread_cond_broadcast(&o->cv_elfos)` (`noel.c:73`) acorda todos os elfos esperando; cada um testa **o próprio** grupo (`gr->estado != GRUPO_CONCLUIDO`, `elfo.c:57`) e só o grupo concluído sai. Os outros voltam a dormir. Isso não muda a espera medida, porque ela termina em `t_inicio_ajuda`.

### Comprova × sugere × não pode concluir
- **Comprova:** na referência, os dois grupos têm a mesma espera máxima (diferença de 0,08 ms, menor que o atraso de qualquer viagem ou ajuda).
- **Sugere:** que com ajuda igual ao intervalo de chegada a espera não acumula. O teste com 4 ms apoia o mecanismo.
- **Não pode concluir:** nada sobre **starvation** em geral. A versão é finita, com 2 grupos; com 2 pontos, o gráfico mostra uma igualdade, não uma tendência.

### Perguntas do professor
- *"p95 de 3 amostras faz sentido?"* Com 3 amostras, o p95 é o máximo. Por isso o gráfico mostra os 5 pontos individuais: quem quiser vê o dado bruto.
- *"Então nenhum grupo pode esperar mais?"* Pode, se a ajuda demorar mais que o intervalo entre os grupos. Com 4 ms de ajuda, a espera sobe ~1,1 ms por grupo.
- *"Por que mostrar um resultado que não confirmou a hipótese?"* Porque é o resultado. A explicação (taxa de chegada = taxa de serviço) é mais informativa que a hipótese.

### Roteiro oral
🎤 "No G3, olhamos a configuração de referência e separamos os dois grupos de elfos. No eixo Y está a maior espera de cada grupo, já que com três elfos o p95 é o máximo. Os pontos cinza são as cinco execuções. A expectativa era que o segundo grupo, mais atrás na fila, esperasse mais. Não esperou: 5,12 contra 5,20 milissegundos. O primeiro grupo espera a viagem acabar; o segundo espera a ajuda ao primeiro. Como os grupos chegam a cada 3 milissegundos e cada ajuda dura 3, o atraso só é passado adiante. Testamos à parte com a ajuda durando 4 milissegundos, e aí sim cada grupo esperou cerca de 1 milissegundo a mais que o anterior."

---

## 7. G4: linha do tempo do Noel

`graficos/G4_linha_tempo.png` · slide 25 · gerado em `graficos.py:186-248`.

### Objetivo
Mostrar **o que o Noel estava fazendo em cada instante** de uma execução real, e onde os grupos esperaram. É o único gráfico que mostra **ordem**, não médias.

### Elementos
- **Eixo X:** tempo desde o sinal de início, em ms. O trecho é **8–23 ms** (de T = 21,36 ms); antes de 8 ms o Noel só dorme.
- **Eixo Y:** três linhas (raias), não uma escala: Noel, grupo 1 (elfos 0–2) e grupo 2 (elfos 3–5).
- **Raia do Noel:** cinza = dormindo/esperando; **laranja = preparando a viagem (5 ms)**; **azul = ajudando o grupo k (3 ms)**.
- **Raias dos grupos:** **hachura verde = grupo pronto esperando o Noel**; azul claro = em ajuda; **traços pequenos = chegada de cada elfo**.
- **Linha roxa sólida:** a 9ª rena chega (10,09 ms). **Linhas verdes tracejadas:** grupo pronto (12,07 e 15,06 ms).

### Interpretação, em ordem (`E06_R10_rep1`, `eventos.csv`)

| t (ms) | Evento | Leitura |
|---|---|---|
| 10,080 | elfo 0 chega | grupo 1 aberto, com 1 elfo |
| 10,091 | 9ª rena | `renas_prontas == 9`, `signal` em `cv_noel` |
| 10,108 | decisão: viagem | 17 µs depois: Noel acordou e retomou o mutex |
| 12,072 | grupo 1 pronto | o Noel está preparando; o `signal` não interrompe |
| 15,061 | grupo 2 pronto | ainda preparando (faltam ~0,1 ms) |
| 15,185 | fim da preparação | broadcast libera as 9 renas |
| 15,200 | decisão: grupo 1 | 15 µs depois; já havia 2 grupos na fila |
| 18,271 → 18,279 | fim do grupo 1, início do grupo 2 | sem pausa: `elfos_ok` já era 1 |
| 21,362 | encerramento | viagem feita e 2/2 grupos concluídos |

- **Não há disputa nesta execução:** quando o Noel decidiu a viagem (10,108), nenhum grupo estava pronto (o grupo 1 só fecha em 12,07). O elfo 0 chegou 11 µs **antes** da 9ª rena, mas um elfo sozinho não é demanda.
- **O que o gráfico mostra de verdade:** a faixa laranja **nunca é cortada** por uma azul, mesmo com dois grupos prontos durante ela. Isso é a **não interrupção** da tarefa em curso.

### Relação com o código e com a sincronização
- **Por que o Noel não é interrompido:** durante a preparação ele **solta o mutex** e dorme em `dormir_ate_ms` (`noel.c:31-33`), não em `cv_noel`. O `signal` do 3º elfo (`elfo.c:53`) não tem ninguém para acordar e "se perde". Isso é seguro porque o estado (`grupos_fechados`) fica gravado e é **relido** no topo do laço (`noel.c:89-90`). É a diferença entre **avisar** e **registrar**: o aviso pode se perder, o predicado não.
- **Por que os elfos conseguem chegar durante a preparação:** como o Noel soltou o mutex, os elfos podem adquiri-lo para se inscrever. Se o Noel segurasse o mutex durante os 5 ms, os traços de chegada se acumulariam no fim da faixa laranja.
- **Estado registrado:** a cor de cada trecho vem do campo `estado_noel` gravado em cada evento por `registrar` (`main.c:33-47`), dentro do mutex. A linha do tempo é um **log real**, não uma reconstrução.

### Comprova × sugere × não pode concluir
- **Comprova:** nesta execução, a ordem foi viagem → grupo 1 → grupo 2, sem interrupção, e os grupos que ficaram prontos durante a viagem esperaram na fila.
- **Sugere:** que o comportamento é o mesmo nas outras repetições (os tempos de `E06_R10` variam < 0,1 ms; o slide 17 mostra o mesmo padrão).
- **Não pode concluir:**
  - nada sobre **prioridade numa disputa** (aqui não houve);
  - nada estatístico (é **uma** execução);
  - a ausência de corrida: o log só mostra o que aconteceu, não o que poderia acontecer em outra ordem de escalonamento.

### Perguntas do professor
- *"O que acontece antes de 8 ms?"* Todas as threads estão dormindo nos sleeps de chegada, e o Noel dorme em `cv_noel` sem demanda.
- *"Este gráfico prova a prioridade às renas?"* Não. Mostra que a tarefa iniciada não é interrompida. A prioridade aparece no slide 18.
- *"Se tirássemos o mutex, este gráfico mudaria?"* Talvez não visualmente: o horário dirige o cenário. O que mudaria são as **garantias**. Sem mutex, o `renas_prontas++` de 9 renas que acordam juntas poderia perder incrementos (`++` não é atômico); o contador não chegaria a 9, a viagem não aconteceria, e o status seria `timeout`. Isso é uma **dedução** [PROVÁVEL]: a versão sem mutex nunca foi executada.

### Roteiro oral
🎤 "O G4 é a linha do tempo de uma execução real, a de referência. Leia de cima para baixo: na primeira faixa está o Noel, e nas outras duas, os grupos. A nona rena chega aos 10,09 milissegundos e, 17 microssegundos depois, o Noel começa a viagem, a faixa laranja. Os traços mostram os elfos chegando um por milissegundo. O grupo 1 fecha aos 12,07, durante a viagem, e espera na faixa hachurada; o grupo 2 fecha aos 15,06, também esperando. A faixa laranja vai até o fim: a preparação não é interrompida, porque durante ela o Noel dorme sem o mutex e só reavalia a fila quando termina. Depois, ele atende os dois grupos sem pausa. Uma observação honesta: aqui não houve disputa, porque quando o Noel decidiu a viagem nenhum grupo estava pronto."

---

## 8. As linhas do tempo dos slides 16, 17 e 18 e as barras do slide 31

São do mesmo tipo do G4 (laranja = viagem, azul = ajuda, roxo = 9ª rena, verde = grupo pronto) e se leem do mesmo jeito.

### Slide 17: antes, junto, depois (real, matriz)
Três linhas do tempo na **mesma escala** (4–36 ms), da repetição 1 de cada cenário. É a **versão visual do G2**:
- **Antes:** a viagem (5–10 ms) termina antes de qualquer elfo chegar; grupos atendidos em ~12 e ~15 ms.
- **Junto:** a viagem (10–15 ms) cobre a formação do grupo 1. É o único caso em que os elfos esperam a viagem.
- **Depois:** grupos atendidos em ~12 e ~15 ms; o Noel fica ocioso de ~18 a 30 ms esperando as renas. Isso explica a **utilização de 32%**: a ociosidade vem do cenário, não da sincronização.

**Conclusão:** o horário das renas muda **quem espera**, nunca as regras: em todos, a viagem acontece uma vez, com 9 renas, e os grupos têm 3 elfos.

### Slide 18: correta × ingênua (real, teste dedicado), o gráfico que testa a prioridade
Mesmo cenário (6 elfos, renas em 30 ms). Com `--teste-prioridade`, o Noel é "segurado" até as **duas demandas** estarem prontas (`noel.c:94-98`), forçando a disputa que a matriz nunca produziu.

| | Correta | Ingênua |
|---|---|---|
| 1ª decisão | viagem (30,47) | grupo 1 (30,11) |
| Ordem | viagem → g1 → g2 | g1 → g2 → viagem |
| Resposta às renas | **18 µs** | **6,145 ms** |
| Violações de prioridade | 0 | **2** |
| T | 41,93 ms | 41,33 ms |
| Espera máxima dos elfos | 25,8 ms | 20,1 ms |

- **Como ler:** as marcas (9ª rena, grupos prontos) estão nos **mesmos lugares** nas duas linhas: o cenário é igual. Muda só a **ordem das barras**, ou seja, só a regra de decisão (`noel.c:117`).
- **A lição mais importante:** a versão ingênua tem **T menor** e elfos esperando **menos**. Pelos números de desempenho, ela pareceria "melhor". Ela está **errada** porque viola a regra. **Desempenho não mede correção.** Por isso o projeto conta violações separadamente.
- As esperas de 20–26 ms são artificiais: o teste segura o Noel de propósito até 30 ms. Não as compare com o G2.

### Slide 16: a rena chega durante uma ajuda (real, fora da matriz)
Com `--renas-ms 13`, a 9ª rena chega (~13,1 ms) **dentro** da ajuda ao grupo 1 (~12,3–15,4 ms). O Noel só a vê no topo do laço, quando as duas demandas estão prontas (**com disputa: 1**), e a viagem vence. A resposta às renas vira **~2,1–2,3 ms** em vez de ~20 µs. Isso é a **prioridade não preemptiva**: vale no próximo ponto de decisão. Reexecutei em 2026-10-28 e obtive a mesma ordem (9ª rena 13,087; decisão pela viagem 15,221; resposta 2,134 ms) [CONFIRMADO 2026-10-28, fora da matriz].

### Slide 31: barras do empate (real, fora da matriz)
Com `--renas-ms 12`, a 9ª rena e o 3º elfo acordam no mesmo instante. As barras mostram em quantas de 30 execuções a 1ª decisão foi a viagem ou o grupo. **A proporção é do escalonador** (12/30 no slide, 8/30 em outra nota, 10/30 na reexecução de 2026-10-28); **o que importa é 0 violações em todas**. A prioridade vale sobre o estado registrado com o mutex: se o 3º elfo pegou o mutex primeiro e o Noel decidiu antes de a rena conseguir o mutex, para o programa a rena ainda não tinha chegado.

### Slide 4: sem mutex × com mutex (hipotético)
Não é medição: é **um entrelaçamento possível** mostrado passo a passo (duas renas lendo o mesmo valor do contador e uma escrita se perdendo). Diga "**pode** acontecer", nunca "aconteceu".

---

## 9. Perguntas transversais do professor

**"O que aconteceria se retirássemos o mutex?"**
Não foi executado [PROVÁVEL; dedução sobre o código]. O cenário é dirigido pelo relógio, então os **gráficos de tempo** quase não mudariam na maioria das execuções. O que se perderia são as **garantias**, e os sintomas apareceriam como `status` diferente de `ok`, não como uma curva:
- `renas_prontas++` sem mutex: as 9 renas acordam juntas e podem perder incrementos → o contador não chega a 9 → sem viagem → `timeout`;
- inscrição no grupo sem mutex: dois elfos podem ocupar a mesma vaga ou entrar num grupo fechado → `violacoes_regras > 0`;
- `pthread_cond_wait` **exige** o mutex; sem ele, o comportamento é indefinido e um aviso pode se perder entre o teste do predicado e o sono → Noel dormindo até o timeout.

O efeito no G1 e no G2 seria **intermitente**: a maioria das execuções pareceria normal, e algumas falhariam. É por isso que condição de corrida não se prova com média.

**"E se retirássemos o semáforo?"**
**Não há semáforo** neste código: são 1 mutex e 4 variáveis de condição (`main.c:131-139`). Não invente o efeito de tirar algo que não existe. O papel que um semáforo teria (contar renas, liberar elfos) é feito por contadores protegidos pelo mutex mais variáveis de condição.

**"Como o comportamento mudaria com mais threads?"**
- **Mais elfos:** a vazão sobe e satura perto de 1000/s (601 com 24, 744 com 48), e a utilização do Noel sobe. A espera dos grupos fica quase constante enquanto ajuda = intervalo de chegada (com 48 elfos, p95 = 6,18 ms: sobe devagar pelo atraso de ~0,07 ms por ciclo).
- **Ajuda mais lenta que a chegada:** a espera cresce linearmente por grupo (seção 6).
- **Mais núcleos não ajudam:** o gargalo é o Noel, um recurso serial. As threads passam quase todo o tempo bloqueadas.
- **Mais renas:** o problema fixa 9; o código também (`NUM_RENAS`).

**"Esse resultado comprova que o problema foi resolvido? Por quê?"**
Não sozinho. Os gráficos mostram que **nas execuções observadas** as regras valeram (25/25 `ok`, 0 violações) e que o desempenho segue o previsto. A **garantia** vem do código: o grupo fecha numa seção crítica, a viagem exige `renas_prontas == 9`, só o Noel decide, com o mutex, testando as renas primeiro, e toda espera é `while` com o predicado. Testes mostram a presença de erros, não a ausência (Dijkstra). Além disso, na matriz nunca houve disputa: a prioridade foi exercitada só pelo teste dedicado e pela ingênua (slide 18). Ver [[Riscos de Sincronização (Papai Noel)]].

**"Onde aparece a preempção nesses gráficos?"**
- **Preempção do SO:** está no **ruído**: as faixas mín–máx e os µs da resposta às renas são o escalonador decidindo quando cada thread volta a rodar.
- **Prioridade da aplicação:** é **não preemptiva** por regra: G4 e slide 16 mostram que uma tarefa iniciada não é interrompida.

São duas coisas diferentes; não as misture.

**"Onde está a seção crítica no gráfico?"**
Em nenhum gráfico ela aparece como faixa: as seções críticas duram µs (inscrever, contar, decidir). As faixas de 3 e 5 ms são feitas **fora** do mutex. O G4 mostra o efeito disso: elfos chegam e se inscrevem **durante** a preparação.

---

## 10. Melhorias sugeridas para os gráficos

São sugestões; nada foi alterado nos scripts ou nos PNGs.

| Gráfico | Problema | Melhoria | Por quê |
|---|---|---|---|
| G1 | Mostra só o medido | Acrescentar a curva prevista N/(15+N)·1000 tracejada e a assíntota de 1000/s | Mostra que o resultado era **previsível** e onde está o teto |
| G1 | A barra de erro some | Dizer na legenda "variação < 3%" ou dar zoom | O leitor procura a barra e não acha |
| G2 | Dois painéis com unidades diferentes | Escrever "µs" em destaque no título do painel direito, ou separar em dois slides | Evita ler 20 µs como 20 ms |
| G2 | O painel direito sugere comparação entre categorias | Anotar "diferenças dentro do ruído; não houve disputa na matriz" | Impede concluir prioridade a partir dele |
| G2, G3 | "p95" com n = 3 ou 6 é o máximo | Renomear o eixo para "maior espera (p95 = máx. com n ≤ 6)" | O nome atual promete algo que não é |
| G2 | A espera mistura "esperar colegas" e "esperar Noel" | Empilhar as duas partes (pronto − pedido e início − pronto) | Mostra que os 2 ms de piso não são sincronização |
| G3 | Só dois pontos, quase iguais | Usar E12 (4 grupos) e sobrepor a curva com ajuda de 4 ms | Mostra **tendência** e o mecanismo da fila |
| G4 | Uma única execução | Dizer no título "rep1 de 5; as outras variam < 0,1 ms" | Antecipa "e as outras?" |
| Falta | Prioridade sem gráfico próprio em `graficos/` | Gerar um G5 com as linhas do tempo correta × ingênua a partir de `dados/teste_prioridade` e `dados/ingenua` | É o único dado que testa a regra de prioridade |
| Slides 16 e 31 | Números digitados no script, sem CSV | Salvar essas execuções em `dados/extra/` e ler de lá | Reprodutibilidade: hoje não dá para reconferir os números exatos |

---

## 11. Exercícios (responda antes de abrir a resposta)

Clique na seta para ver a resposta. Tente **falar a resposta em voz alta** primeiro: é isso que você fará na apresentação.

> [!question]- 1. No G2, o painel direito mostra 18 µs no caso "junto" e 21 µs no "depois". Dá para dizer que as renas são atendidas mais rápido quando chegam junto com os elfos?
> Não. As faixas mín–máx (8–34 µs e 9–45 µs) se sobrepõem quase inteiras: a diferença de 3 µs está dentro do ruído do escalonador. Nos três casos, o Noel está dormindo em `cv_noel` quando a 9ª rena chega, então o mecanismo é o mesmo. Passo 5 do método: diferença menor que a variação → nada a concluir.

> [!question]- 2. Um colega diz: "No G2, a espera de 2,1 ms com as renas antes mostra o custo da sincronização". Está certo?
> Não. 2 ms é o elfo 0 esperando os colegas: ele chega em 10 ms e o grupo só fecha em 12 ms, quando chega o elfo 2. A métrica é `t_inicio_ajuda − t_pedido`, que inclui a formação do grupo. O custo de acordar o Noel aparece no último elfo do grupo: ~0,025 ms.

> [!question]- 3. Se `ajuda_ms` fosse 2 ms (mais rápida que os 3 ms entre grupos), o que aconteceria com o G3?
> O grupo 1 continuaria esperando a viagem (~5,1 ms para o elfo 0). Mas o grupo 2 fica pronto em ~15,06 e o Noel terminaria o grupo 1 em ~17,2: o grupo 2 esperaria **menos** que o grupo 1. Conferido em 2026-10-28 com `--elfos 6 --renas-ms 10 --ajuda-ms 2` (fora da matriz): grupo 1 = 5,14 ms, grupo 2 = 4,22 ms. A fila **esvazia**: o atendimento é mais rápido que a chegada, e o atraso inicial vai sendo absorvido.

> [!question]- 4. A versão ingênua terminou em 41,33 ms e a correta em 41,93 ms, com os elfos esperando menos na ingênua. Então a ingênua é melhor?
> Não. Ela é mais "rápida" porque atende os elfos antes, o que viola a regra do problema: 2 violações de prioridade e renas esperando 6,1 ms em vez de 18 µs. Métricas de desempenho não medem correção; por isso o programa conta violações separadamente (`noel.c:118-119`).

> [!question]- 5. O professor aponta o G4 e pergunta: "Aqui o Noel escolheu as renas em vez dos elfos, certo?"
> Não houve escolha entre as duas. Quando o Noel decidiu (10,108 ms), havia só as renas: o grupo 1 só fechou em 12,07. O G4 mostra a não interrupção da viagem, não a prioridade numa disputa. A disputa aparece no slide 18 (teste dedicado) e no slide 16 (`--renas-ms 13`).

> [!question]- 6. Se uma das 5 execuções de 6 elfos tivesse travado até o timeout (Noel sem ser acordado), como isso apareceria no G1?
> **Não apareceria como ponto.** O `graficos.py` filtra só as execuções com status `ok` (`graficos.py:71`), então a execução com `timeout` sairia do cálculo. O sintoma estaria no **título** ("n = 4 execuções por ponto", porque o título usa o menor n) e em `taxa_validas` < 1 em `tabela_esperas.csv`. Por isso, antes de ler qualquer curva, confira a taxa de execuções válidas (25/25). Depois, investigue o `eventos.csv` daquela execução para ver qual evento faltou, por exemplo uma `nona_rena` que nunca veio.

> [!question]- 7. Por que o G4 não serve para provar ausência de condição de corrida?
> Porque é um log de **uma** ordem de escalonamento. Uma corrida depende de uma ordem específica, talvez rara, que não ocorreu nesta execução. A ausência de corrida vem da análise: todo acesso ao estado compartilhado é feito com o mutex. Ferramentas como TSan e Helgrind ajudariam, mas não foram executadas.

> [!question]- 8. No caso "depois" (renas em 30 ms), a utilização do Noel é 32%. Isso indica que a sincronização está ineficiente?
> Não. De ~18 a 30 ms, o Noel não tem demanda: os grupos já foram atendidos e as renas ainda não chegaram. Ele dorme em `cv_noel`, sem gastar CPU. A ociosidade vem do cenário. Ineficiência seria o Noel dormindo com demanda pronta, e o G4 e o slide 17 mostram que isso não acontece.

> [!question]- 9. Descreva o que você esperaria ver no G4 se o Noel segurasse o mutex durante os 5 ms da preparação.
> Os elfos que acordam em 11 e 12 ms ficariam bloqueados no `pthread_mutex_lock` (`elfo.c:27`) até ~15,2 ms. No `eventos.csv`, as chegadas dos elfos 1 a 5 apareceriam amontoadas logo depois do fim da preparação, e o grupo 1 só "ficaria pronto" depois da viagem. A espera medida (`t_inicio_ajuda − t_pedido`) diminuiria artificialmente, porque o `t_pedido` seria gravado tarde. É uma dedução, não foi executada.

> [!question]- 10. Em 30 execuções do empate (`--renas-ms 12`), a primeira decisão foi a viagem em 12, 8 ou 10 vezes, conforme a rodada. Isso indica um bug?
> Não. Quem adquire o mutex primeiro, a 9ª rena ou o 3º elfo, é decidido pelo escalonador, e a POSIX não garante ordem no mutex. Se o grupo é registrado antes da rena, para o programa a rena ainda não chegou, e atender o grupo não viola a regra. O dado que importa é 0 violações em todas as rodadas.
