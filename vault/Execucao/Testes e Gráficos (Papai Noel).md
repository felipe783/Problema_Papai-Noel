# Testes e Gráficos (Papai Noel)

Como os experimentos foram feitos, o que os números dizem e como apresentar G1–G4. Todos os valores vêm de `tema11_papai_noel/dados/` (rodada de 2026-10-28) [CONFIRMADO 2026-10-28]. Os PNGs estão em `tema11_papai_noel/graficos/`, fora do vault, então abra-os pelo explorador de arquivos ou pelos slides. Como reproduzir (comandos, flags, venv): [[Execução e Flags (Papai Noel)]]. Índice: [[_Papai-Noel]].

> Esta nota é o **resumo dos números**. Para aprender a ler cada gráfico (eixos, elementos, mecanismo no código, o que comprova e o que não comprova, roteiro oral e exercícios), use [[Interpretação dos Gráficos (Papai Noel)]].

## Método em uma frase

São **5 configurações × 5 repetições = 25 execuções**, intercaladas por repetição, com o tempo medido a partir do sinal de início comum (`CLOCK_MONOTONIC`). As sementes 11, 22, 33, 44 e 55 são só o **id da repetição**, porque o programa não tem aleatoriedade; a variação vem do escalonador do SO e da latência dos timers.

| Configuração | Elfos | Renas | Conjunto |
|---|---|---|---|
| E06_R10 | 6 | 10 ms (junto) | referência |
| E03_R10, E12_R10 | 3, 12 | 10 ms | conjunto 1 (varia elfos) |
| E06_R05, E06_R30 | 6 | 5 ms (antes), 30 ms (depois) | conjunto 2 (varia renas) |

Além da matriz, foram feitos:

| Teste | Resultado |
|---|---|
| Piloto (15 execuções) | maior T = 35,211 ms, o que levou ao timeout de 2000 ms (≈ 56×) |
| Mecanismo de timeout (`--timeout-ms 5`) | status `timeout`, 0/6 pedidos, sem travar |
| `--teste-prioridade` | **PASSOU**: 1ª decisão = renas, 6/6 elfos, 0 violações |
| `--ingenua` (mesmo cenário) | 2 violações de prioridade; resposta às renas 6,145 ms |
| Estresse (3/10, 12/5 e 12/30, 100× cada) | 300/300 `ok`, maior T = 35,688 ms |

## Métricas: definições exatas

- **T**: de `t0` ao encerramento de Noel (`noel.c:137`).
- **Vazão**: `concluidos / (T_ms / 1000)` pedidos/s.
- **Espera do elfo**: `t_inicio_ajuda − t_pedido` (o pedido é gravado em `elfo.c:32`, o início em `noel.c:56`).
- **p95**: a posição ⌈0,95·n⌉ (base 1) das esperas ordenadas (`metricas.c:23`). Com n = 3 ou 6, **o p95 é o máximo**.
- **Resposta às renas**: `t_ini_preparo − t_nona` (`noel.c:27` menos `rena.c:31`).
- **Utilização de Noel**: tempo em ajuda ou preparação / T.

## Resultados (média das 5 repetições; mín–máx entre parênteses)

| Config. | Vazão (pedidos/s) | Espera média (ms) | p95 (ms) | Resposta às renas (µs) | Util. Noel |
|---|---|---|---|---|---|
| E03_R10 | 163,4 (160,0–164,3) | 4,21 | 5,21 (5,11–5,56) | 24 | 44,8% |
| **E06_R10** | **280,9 (280,2–281,3)** | 4,17 | **5,20 (5,17–5,25)** | 18 | 52,5% |
| E12_R10 | 436,2 (435,4–437,0) | 4,25 | 5,37 (5,32–5,41) | 20 | 63,1% |
| E06_R05 | 328,7 (328,5–328,9) | 1,06 | 2,10 (2,10–2,11) | 20 | 61,5% |
| E06_R30 | 170,0 (168,9–170,6) | 1,07 | 2,11 (2,10–2,12) | 21 | 32,0% |

Taxa de execuções válidas: **25/25 (100%)**, com 0 violações de prioridade e 0 de regras.

> **Por que tão pouca variação?** O cenário é dirigido pelo relógio: os instantes de chegada e as durações são fixos. A variação entre repetições é só o "ruído" do SO, abaixo de 1% na maioria dos casos. A exceção é a repetição 2 de E03_R10, com T = 18,754 ms contra ~18,26 ms nas outras, por um atraso do sistema. Ela foi mantida nos dados, sem refazer.

## Como apresentar cada gráfico

Use sempre o mesmo roteiro: **o que ficou fixo e o que variou → a tendência → que parte do código explica → a hipótese se confirma? → a diferença é maior que a variação?**

### G1: vazão × nº de elfos (`G1_vazao_elfos.png`)

- **Fixo:** renas em 10 ms. **Variou:** 3, 6 e 12 elfos, com 5 execuções por ponto.
- **Tendência:** 163 → 281 → 436 pedidos/s.
- **Por quê:** existe um custo fixo de ~15 ms (10 ms até o 1º elfo + 5 ms de viagem). Depois disso, a **fila FIFO** de grupos faz Noel atender um grupo atrás do outro. A previsão é T ≈ 15 + 3·(N/3) ms, ou seja, 167, 286 e 444 pedidos/s; o medido ficou cerca de 2% abaixo por causa da latência dos sleeps.
- **Hipótese H<sub>A</sub>** ("a vazão cresce com N"): **confirmada**. As diferenças (> 100 pedidos/s) são muito maiores que a faixa mín–máx.
- **Fala curta:** "Mais elfos diluem o custo fixo do começo: a vazão quase triplica, mas ainda está longe do limite teórico de 1000 pedidos/s, que é 3 elfos a cada 3 ms."

### G2: chegada das renas × p95 da espera (`G2_p95_renas.png`)

- **Fixo:** 6 elfos. **Variou:** renas antes, junto e depois. São categorias, por isso os pontos não são ligados por linha.
- **Tendência:** junto = 5,20 ms; antes = 2,10 ms; depois = 2,11 ms.
- **Por quê:** só no caso "junto" a **prioridade às renas** põe a viagem (10–15 ms) em cima da formação do 1º grupo (pronto em ~12 ms). Nos outros casos, Noel está livre quando cada grupo fecha, e a espera é só o tempo de completar o grupo: o 1º elfo espera ~2 ms pelos outros dois.
- **Painel direito:** a resposta às renas fica entre 18 e 21 µs em média nos três casos. É o custo de acordar Noel (o `signal` em `rena.c:33` mais a reaquisição do mutex).
- **Hipótese H<sub>B</sub>:** **confirmada**. Uma diferença de ~3 ms contra variação < 0,1 ms.
- **Fala curta:** "É o preço visível da prioridade: as renas esperam microssegundos, e quem paga são os elfos do primeiro grupo, que esperam ~3 ms a mais."

### G3: p95 por grupo na referência (`G3_p95_grupo.png`)

- **Fixo:** referência. **Variou:** o grupo (1 ou 2), com 5 execuções × 3 elfos = 15 amostras por grupo.
- **Resultado:** grupo 1 = 5,12 ms (5,10–5,18); grupo 2 = 5,20 ms (5,17–5,25). São **praticamente iguais**.
- **Por quê:** o grupo 1 espera o fim da viagem, e o grupo 2 espera o fim da ajuda ao grupo 1. Como os grupos chegam a cada 3 ms e cada ajuda dura 3 ms, o atraso inicial **se propaga sem crescer**.
- **Expectativa intuitiva** ("o 2º grupo espera mais"): **não se confirmou**. Vale contar isso na apresentação: mostra que o grupo interpretou o resultado em vez de forçar a hipótese.

### G4: linha do tempo de Noel (`G4_linha_tempo.png`, execução E06_R10_rep1)

- **Mostra:** faixas de estado (dormindo, preparando a viagem, ajudando o grupo k), as marcas da 9ª rena e de cada "grupo pronto" e o trecho de 8 a 23 ms.
- **Leitura:** a 9ª rena chega em ~10,1 ms e Noel prepara até ~15,2 ms. Os dois grupos ficam prontos **durante** a preparação (12,07 e 15,06 ms) e esperam, na faixa hachurada, **sem interromper** a preparação. Depois Noel fica ocupado sem pausa.
- **Fala curta:** "Aqui se vê a disputa real: os elfos ficam prontos enquanto Noel prepara a viagem e entram na fila. A preparação não é interrompida."

## Perguntas prováveis sobre os gráficos

- **"Por que só 5 repetições?"** É o que o enunciado pede, e a variação observada é muito menor que as diferenças entre configurações. Mais repetições não mudariam as conclusões.
- **"O p95 de 3 amostras faz sentido?"** Com n = 3, ⌈0,95·3⌉ = 3, então o p95 é o **máximo**. Por isso o G3 mostra também os pontos individuais e o n de amostras.
- **"A utilização de 32% em E06_R30 é ruim?"** Não indica ineficiência da sincronização: Noel fica ~12 ms dormindo à espera das renas, que chegam tarde. A ociosidade vem do cenário.
- **"Esses números provam que não há corrida?"** Não. Eles mostram que as regras valeram em todas as execuções observadas. A garantia vem da análise do código ([[Riscos de Sincronização (Papai Noel)]]).

Respostas completas para a banca: [[Perguntas da Apresentação (Papai Noel)]].
