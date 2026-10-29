# Saída do Programa (Papai Noel)

O que cada campo impresso pelo `simulacao` significa, **onde no código ele nasce** e o que ele prova (ou não prova) sobre a sincronização. Índice: [[_Papai-Noel]]. Como rodar e todas as flags: [[Execução e Flags (Papai Noel)]]. A execução fase a fase: [[Fluxo do Código e Sincronização (Papai Noel)]].

> Exemplos reais de 2026-10-28, gerados num binário compilado numa pasta temporária, com `--out` para pastas temporárias (nada foi escrito em `dados/`) [CONFIRMADO 2026-10-28]. Os tempos mudam um pouco a cada execução (ruído do SO); a estrutura e as contagens, não. Linhas de código conferidas no mesmo dia.

## Sumário

1. [[#1. O caminho da saída: do evento ao console]]
2. [[#2. Os três exemplos usados nesta nota]]
3. [[#3. A linha de resumo, campo por campo]]
4. [[#4. As linhas [teste-prioridade]]]
5. [[#5. Status e código de saída]]
6. [[#6. Os três CSVs]]
7. [[#7. Lendo as três execuções lado a lado]]
8. [[#8. O que a saída não prova]]
9. [[#9. Fala pronta para a apresentação]]

## 1. O caminho da saída: do evento ao console

A saída é produzida em **duas fases separadas**. Isso é uma decisão de projeto: imprimir durante a simulação atrasaria as threads e distorceria os tempos medidos.

| Fase | Quando | O que acontece | Onde |
|---|---|---|---|
| **Coleta** | durante a simulação, sempre com o mutex adquirido | as threads anotam instantes (`t_pedido`, `t_nona`, `t_ini_preparo`...), somam contadores (`decisoes`, `violacoes_*`, `ocupado_ms`) e chamam `registrar()`, que guarda um evento num vetor em memória | `noel.c`, `elfo.c`, `rena.c`, `registrar` em `main.c:33-46` |
| **Cálculo e exportação** | depois de **todos** os `pthread_join` | `calcular_metricas` transforma os dados brutos em métricas; `exportar_csv` grava os 3 CSVs; só então o `printf` mostra a linha de resumo | `main.c:214-264`, `metricas.c:29-81`, `csv.c:67-128` |

```
threads (com mutex) ──registrar()/contadores──▶ struct Oficina (memória)
                                                      │  pthread_join de todas
                                                      ▼
                                     calcular_metricas()  ─▶ struct Metricas
                                                      ▼
                          exportar_csv()  ─▶ resumo.csv, eventos.csv, espera_elfos.csv
                                                      ▼
                          printf (linha de resumo) ─▶ [teste-prioridade] ─▶ código de saída
```

Consequências:

- **Não há concorrência no cálculo.** `metricas.c` roda com uma única thread viva (comentário em `metricas.c:3`), então não precisa de mutex.
- **Os valores são coerentes entre si.** Todos foram escritos sob o mesmo mutex que protege as decisões, então os contadores não ficam "no meio de uma atualização".
- **Todos os tempos são relativos a `t0`**, o instante da largada (`main.c:210`), medidos com `CLOCK_MONOTONIC` por `ms_desde_inicio` (`tempo.c:38-41`). `t = 10.000` significa "10 ms depois da largada".
- **O vetor de eventos tem capacidade fixa**: `4·elfos + 2·9 + 16` (`main.c:114`). Se encher, `registrar` não grava e soma `eventos_perdidos` (`main.c:36-38`), o que faz o status virar `violacao` (`metricas.c:77`). Isso nunca aconteceu nas execuções registradas.

## 2. Os três exemplos usados nesta nota

Comandos rodados de dentro de `src/`, cada um com sua própria pasta de saída:

```bash
./simulacao --elfos 6 --renas-ms 10 --out /tmp/papai/                                # normal
./simulacao --elfos 6 --renas-ms 30 --out /tmp/papai/ --teste-prioridade             # teste
./simulacao --elfos 6 --renas-ms 30 --out /tmp/papai/ --teste-prioridade --ingenua   # ingênua
```

**Normal** (código de saída 0):

```
E06_R10_rep1: status=ok T=21.348 ms concluidos=6/6 vazao=281.05 pedidos/s espera_p95=5.202 ms resposta_renas=0.016 ms viol_prio=0 viol_regras=0 decisoes=3 (com disputa: 0) util_noel=52.5%
```

**Teste de prioridade** (código de saída 0):

```
teste_E06_R30_rep1: status=ok T=41.404 ms concluidos=6/6 vazao=144.91 pedidos/s espera_p95=25.251 ms resposta_renas=0.023 ms viol_prio=0 viol_regras=0 decisoes=3 (com disputa: 1) util_noel=27.1%
[teste-prioridade] disputa na 1a decisão (renas e grupo prontos): SIM
[teste-prioridade] primeira decisão = renas -> OK
[teste-prioridade] elfos atendidos = 6/6 -> OK
[teste-prioridade] violações (prioridade=0, regras=0) -> OK
[teste-prioridade] RESULTADO: PASSOU
```

**Ingênua** (código de saída 1, **falhar é o esperado**):

```
teste_ingenua_E06_R30_rep1: status=violacao T=41.336 ms concluidos=6/6 vazao=145.15 pedidos/s espera_p95=20.125 ms resposta_renas=6.172 ms viol_prio=2 viol_regras=0 decisoes=3 (com disputa: 2) util_noel=27.1%
[teste-prioridade] disputa na 1a decisão (renas e grupo prontos): SIM
[teste-prioridade] primeira decisão = elfos -> FALHOU
[teste-prioridade] elfos atendidos = 6/6 -> OK
[teste-prioridade] violações (prioridade=2, regras=0) -> FALHOU
[teste-prioridade] RESULTADO: FALHOU
```

## 3. A linha de resumo, campo por campo

O `printf` está em `main.c:231-236`. Para cada campo: o que é, como é calculado, onde o dado bruto nasce e o que ele diz sobre a sincronização.

### 3.1 Nome da execução: `E06_R10_rep1`

- **O que é:** um rótulo que identifica a execução nos CSVs (coluna `execucao`).
- **Como é montado:** `montar_id` (`csv.c:19-40`). `E%02d` = número de elfos, `R%02d` = `--renas-ms`, `_rep%d` = `--rep`. Prefixos: `teste_` com `--teste-prioridade`, `ingenua_` com `--ingenua`, os dois juntos dão `teste_ingenua_`.
- **Detalhe:** o mesmo código também define a coluna `conjunto` do `resumo.csv` (`referencia` para 6 elfos/10 ms, `1` para a série com renas em 10 ms, `2` para a série com 6 elfos, `fora` para o resto). É assim que `graficos.py` separa as séries.
- **Sincronização:** nenhuma; é só rótulo.

### 3.2 `status=ok`

- **O que é:** o veredito da execução: `ok`, `timeout` ou `violacao`.
- **Como é decidido** (`metricas.c:75-80`), nesta ordem:
  1. `timeout` se Noel desistiu de esperar (`o->abortar`);
  2. `violacao` se `violacoes_prioridade > 0`, `violacoes_regras > 0` ou `eventos_perdidos > 0`;
  3. `ok` caso contrário.
- **Sincronização:** `ok` significa que **nenhum dos verificadores embutidos** disparou (ver 3.7 e 3.8). É a soma de todas as checagens.

### 3.3 `T=21.348 ms`

- **O que é:** duração da execução, da largada até Noel encerrar.
- **Onde nasce:** `o->t_encerramento = ms_desde_inicio(o)` quando Noel sai do laço (`noel.c:137`, ou `noel.c:140` no timeout). `metricas.c:43` copia para `m->T_ms`.
- **Por que acaba ali:** Noel só sai do laço quando `viagem_concluida && grupos_concluidos == n_grupos` (`noel.c:86-87`), isto é, quando as duas demandas terminaram. Na execução normal: 21,345 (fim da 2ª ajuda) → 21,348 (`encerramento`).
- **Não inclui** criar as threads, os joins, o cálculo e a gravação dos CSVs. Mede só a simulação.

### 3.4 `concluidos=6/6`

- **O que é:** elfos atendidos / elfos previstos (`--elfos`).
- **Onde nasce:** quando uma ajuda termina, Noel soma 1 em `atendimentos[membro]` para os 3 elfos do grupo (`noel.c:66-67`). `metricas.c:45-48` conta quantos elfos têm `atendimentos >= 1`.
- **Sincronização:** um elfo só é atendido se entrou num grupo, o grupo fechou com 3 e Noel o escolheu. `6/6` mostra que nenhum elfo ficou para trás (sem starvation nesta versão finita).
- **Checagem extra:** se algum elfo tiver `atendimentos != 1` (nunca atendido, ou atendido duas vezes), `metricas.c:36-38` soma uma violação de regra.

### 3.5 `vazao=281.05 pedidos/s`

- **O que é:** pedidos de elfos atendidos por segundo.
- **Fórmula** (`metricas.c:49`): `concluidos / (T_ms / 1000)`. Exemplo: `6 / 0,021348 = 281,05`.
- **Leitura:** depende de T, e T é dominado pelos sleeps simulados (chegadas, `--preparo-ms`, `--ajuda-ms`), não pelo custo do mutex. Compare vazões só entre execuções com os mesmos tempos simulados. O teste de prioridade tem metade da vazão (144,91) porque T dobrou: Noel ficou parado de propósito até 30 ms.

### 3.6 `espera_p95=5.202 ms`

- **O que é:** o percentil 95 do tempo que cada elfo esperou, entre pedir ajuda e a ajuda começar.
- **Onde nascem os dados:**
  - `t_pedido[id]`: quando o elfo entra na seção crítica, logo depois de "chegar" (`elfo.c:32`);
  - `t_inicio_ajuda[membro]`: quando Noel começa a ajudar o grupo, gravado para os 3 membros (`noel.c:54-56`).
- **Cálculo:** `espera = t_inicio_ajuda − t_pedido` para cada elfo atendido (`metricas.c:55-63`). `percentil95` ordena e pega a posição ⌈0,95·n⌉, calculada em inteiros como `(95n + 99) / 100` (`metricas.c:17-27`).
- **Com 6 elfos:** ⌈5,7⌉ = 6ª posição = a **maior** espera. Por isso, nesta configuração, p95 = máximo.
- **`-1.000`** quer dizer "sem amostras" (nenhum elfo teve a ajuda iniciada, por exemplo num timeout). No CSV aparece `N/A` (`csv.c:59-65`).
- **Sincronização:** a espera mede quanto tempo o elfo ficou bloqueado. Ela inclui o tempo até completar o grupo de 3 (o 1º elfo espera os outros 2) **e** o tempo em que Noel estava ocupado. Na execução normal, o grupo 1 esperou 3,1 a 5,1 ms porque Noel estava preparando o trenó.

### 3.7 `resposta_renas=0.016 ms`

- **O que é:** quanto Noel demorou para começar a preparar o trenó depois que a 9ª rena chegou.
- **Onde nasce:**
  - `t_nona`: gravado pela rena que faz `renas_prontas` chegar a 9 (`rena.c:89-92`), logo antes do `pthread_cond_signal(&cv_noel)` (`rena.c:94`);
  - `t_ini_preparo`: gravado por Noel em `preparar_viagem` (`noel.c:27`).
- **Fórmula** (`metricas.c:70`): `t_ini_preparo − t_nona`, ou `-1` se a viagem não começou.
- **Sincronização:** este é o número que mais diretamente mede a **prioridade**.
  - Correta: 0,016 a 0,023 ms. É só o tempo de Noel acordar do `cond_wait`, readquirir o mutex e decidir.
  - Ingênua: **6,172 ms**. Noel atendeu dois grupos de elfos antes (2 × ~3 ms).
  - Se as renas chegassem durante uma ajuda, a resposta seria o resto da ajuda, porque **a ajuda nunca é interrompida** (comentário em `noel.c:6-7`). Isso é correto, não violação.

### 3.8 `viol_prio=0`

- **O que é:** quantas vezes Noel escolheu um grupo de elfos **quando as 9 renas estavam prontas**.
- **Onde nasce** (`noel.c:117-119`), no momento da decisão, com o mutex adquirido:

```c
int escolhe_renas = c->ingenua ? !elfos_ok : renas_ok;
if (!escolhe_renas && renas_ok)
    o->violacoes_prioridade++; /* elfos com as 9 renas prontas */
```

- **Os predicados** (`noel.c:89-90`):
  - `renas_ok = renas_prontas == 9 && !viagem_iniciada`;
  - `elfos_ok = proximo_grupo < grupos_fechados` (há grupo fechado esperando na fila).
- **Por que é confiável:** o verificador olha exatamente os mesmos predicados que Noel usou para decidir, lidos dentro da mesma seção crítica. Nenhuma outra thread consegue mudar o estado entre a leitura e a decisão.
- **Ingênua = 2:** as duas decisões tomadas com renas prontas foram para elfos (30,10 ms e 33,18 ms).

### 3.9 `viol_regras=0`

Soma de **todas** as outras regras quebradas. Cada `violacoes_regras++` do código é um verificador:

| Regra | Onde é checada | Quando dispara |
|---|---|---|
| Viagem só com 9 renas | `noel.c:21-22` | `preparar_viagem` chamado com `renas_prontas < 9` |
| Ajuda só a grupo de exatamente 3, já fechado | `noel.c:48-49` | grupo com `n != 3` ou estado diferente de `GRUPO_PRONTO` |
| Uma atividade por vez | `noel.c:111-112` | Noel decide com `ajuda_em_curso` ligado |
| Nenhum elfo invade grupo fechado | `elfo.c:36-37` | o grupo aberto não está `GRUPO_ABERTO` ou já tem 3 |
| Cada elfo atendido exatamente uma vez | `metricas.c:36-38` | `atendimentos[e] != 1` no fim |
| A viagem acontece | `metricas.c:39-40` | `viagem_concluida == 0` no fim |

As duas últimas só são checadas se **não** houve timeout (`metricas.c:35`), porque num timeout os pendentes já estão explicados pelo status.

`viol_regras=0` até na ingênua mostra que **só a prioridade** foi invertida; o resto da sincronização continua correto.

### 3.10 `decisoes=3 (com disputa: 0)`

- **O que é:** quantas vezes Noel acordou com trabalho e escolheu o que fazer, e em quantas dessas havia **disputa**, isto é, renas **e** grupo prontos ao mesmo tempo.
- **Onde nasce** (`noel.c:113-115`):

```c
o->decisoes++;
if (renas_ok && elfos_ok)
    o->decisoes_com_disputa++;
```

- **Por que sempre dá 3 com 6 elfos:** 1 preparação + 2 grupos (6 ÷ 3). Acordar sem trabalho (aviso antigo, acordar espúrio) **não** conta: o `while` volta a dormir antes de chegar na decisão (`noel.c:100-108`).
- **Por que a disputa importa:** se `com disputa: 0`, a regra de prioridade **não foi exercitada** nessa execução. `viol_prio=0` aí é verdadeiro, mas não prova nada. Isso aconteceu em **todas** as 25 execuções da matriz; só o teste de prioridade (1 disputa) e a ingênua (2) criam disputa (ver [[#8. O que a saída não prova]]).

### 3.11 `util_noel=52.5%`

- **O que é:** fração de T em que Noel estava trabalhando (preparando ou ajudando) em vez de dormindo.
- **Onde nasce:** ao fim de cada atividade, Noel soma a duração em `ocupado_ms` (`noel.c:36` para a preparação, `noel.c:65` para a ajuda). `metricas.c:71`: `ocupado_ms / T_ms`.
- **Exemplo:** na execução normal, a preparação levou 5,07 ms e as ajudas 3,07 + 3,07 ms, total 11,21 ms de 21,348 ms = 52,5%.
- **Leitura:** a soma é sempre ≈ `preparo_ms + n_grupos × ajuda_ms` (5 + 2×3 = 11 ms com os padrões). O que muda entre execuções é T. Nos testes com renas em 30 ms, T ≈ 41 ms, então a utilização cai para 27%.

## 4. As linhas `[teste-prioridade]`

Só aparecem com `--teste-prioridade` (`main.c:239-254`). Nesse modo, Noel só começa a trabalhar quando renas **e** grupo estão prontos juntos (`noel.c:94-98`), o que força uma disputa na 1ª decisão.

Detalhe de sincronização: quando o grupo 1 fecha (12,08 ms), o elfo dá `signal` em `cv_noel`, Noel acorda, vê `liberado = 0` e volta a dormir. Esse é exatamente o comportamento do `while`: acordar não basta, o predicado é reavaliado.

| Linha | Variável | Condição para OK | Onde é gravada |
|---|---|---|---|
| `disputa na 1a decisão: SIM` | `ok4` | `decisoes_com_disputa >= 1` | `noel.c:114-115` |
| `primeira decisão = renas -> OK` | `ok1` | `primeira_decisao == 1` (1 = renas, 2 = elfos) | `noel.c:120-121` |
| `elfos atendidos = 6/6 -> OK` | `ok2` | `concluidos == previstos` | `metricas.c:45-48` |
| `violações (...) -> OK` | `ok3` | `viol_prio == 0 && viol_regras == 0 && !abortar` | contadores das seções 3.8 e 3.9 |
| `RESULTADO: PASSOU` | `passou` | `ok1 && ok2 && ok3 && ok4` | `main.c:252-254` |

`ok4` é o que dá valor ao teste: ele garante que a situação difícil **realmente aconteceu**. Sem ele, um teste em que as renas nunca disputassem com os elfos poderia "passar" sem testar nada.

## 5. Status e código de saída

`main.c:238-264`:

| Situação | Código |
|---|---|
| Execução normal com `status=ok` | 0 |
| `--teste-prioridade` com `RESULTADO: PASSOU` | 0 |
| `--teste-prioridade` com `RESULTADO: FALHOU` (inclui a ingênua) | 1 |
| Execução normal com `status` diferente de `ok` (`timeout` ou `violacao`) | 2 |
| Falha ao gravar algum CSV (por exemplo, pasta do `--out` inexistente); vale em qualquer modo e sobrescreve os anteriores | 1 |
| `--help` ou argumento inválido (antes de simular) | 64 (ver [[Execução e Flags (Papai Noel)]]) |

Para ver o código: rode o programa e depois `echo $?`. O `run_experimentos.sh` usa esses códigos para saber se cada execução deu certo.

## 6. Os três CSVs

Gravados por `exportar_csv` (`csv.c:67-128`) em **modo de acréscimo** (`fopen(..., "a")`, `csv.c:48`). O cabeçalho só é escrito se o arquivo estava vazio (`csv.c:53-54`). Por isso várias execuções se acumulam na mesma pasta, separadas pela coluna `execucao`.

### 6.1 `resumo.csv`: uma linha por execução

As mesmas métricas do console, mais algumas (`csv.c:76-89`):

| Coluna | De onde vem | Observação |
|---|---|---|
| `tema` | fixo `11_papai_noel` | |
| `configuracao`, `conjunto` | `montar_id` | ver 3.1 |
| `repeticao`, `semente` | `--rep`, `--semente` | a semente **só é gravada**: não há aleatoriedade no programa |
| `elfos`, `renas_ms` | flags | |
| `T_ms`, `previstos`, `concluidos`, `vazao_pedidos_s` | 3.3 a 3.5 | |
| `espera_media_ms`, `espera_p95_ms`, `espera_max_ms`, `n_amostras` | `metricas.c:51-67` | média e máximo só aparecem aqui, não no console |
| `resposta_renas_ms` | 3.7 | `N/A` se a viagem não começou |
| `violacoes_prioridade`, `violacoes_regras` | 3.8 e 3.9 | |
| `utilizacao_noel` | 3.11 | fração (0,5251), não porcentagem |
| `status` | 3.2 | |

`decisoes` e `com disputa` **não** estão no `resumo.csv`; só aparecem no console. Por isso a contagem de disputas da matriz foi tirada de `dados/log_execucao.txt`, que guarda a saída do console.

### 6.2 `eventos.csv`: a linha do tempo

Colunas: `execucao, t_ms, participante, tipo, evento, estado_noel, grupo_id` (`csv.c:96-104`).

- `participante`: id da thread dentro do tipo (elfo 0..N-1, rena 1..9, Noel 0).
- `estado_noel`: o estado de Noel **no momento em que o evento foi registrado** (`registrar` copia `o->estado`, `main.c:45`).
- `grupo_id`: grupo do elfo (1, 2...) ou grupo da ajuda; vazio para renas e para a preparação.

Cada evento é registrado num ponto exato do código, sempre com o mutex adquirido:

| Evento | Quem registra | Onde | O que significa |
|---|---|---|---|
| `chegada` (elfo) | elfo | `elfo.c:43` | entrou no grupo aberto |
| `grupo_pronto` | 3º elfo | `elfo.c:52` | fechou o grupo e vai acordar Noel (`signal`, `elfo.c:53`) |
| `chegada` (rena) | rena | `rena.c:90` | incrementou `renas_prontas` |
| `nona_rena` | 9ª rena | `rena.c:93` | vai acordar Noel (`signal`, `rena.c:94`) |
| `decisao` | Noel | `noel.c:125` ou `noel.c:130` | escolheu (o `estado_noel` já mostra a escolha: `preparando` ou `ajudando`) |
| `inicio_preparacao` / `fim_preparacao` | Noel | `noel.c:28` / `noel.c:40` | o sleep da preparação acontece **entre** os dois, sem o mutex |
| `inicio_ajuda` / `fim_ajuda` | Noel | `noel.c:57` / `noel.c:72` | idem para a ajuda |
| `encerramento` | Noel | `noel.c:138` | as duas demandas terminaram |
| `timeout` | Noel | `noel.c:104` | o `timedwait` estourou o prazo |

Repare num detalhe da execução normal: entre `inicio_preparacao` (10,114) e `fim_preparacao` (15,184), os elfos continuam chegando e o grupo 2 fecha (15,076), com `estado_noel = preparando`. Isso mostra que **Noel solta o mutex durante a atividade** (`noel.c:31-33`): se ele segurasse o mutex, nenhum elfo conseguiria se registrar até a preparação acabar.

### 6.3 `espera_elfos.csv`: uma linha por elfo

Colunas: `execucao, elfo_id, grupo_id, t_pedido_ms, t_inicio_ajuda_ms, espera_ms` (`csv.c:111-124`). São os dados brutos da seção 3.6, de onde `graficos.py` tira as esperas.

Na execução normal:

| Elfo | Grupo | Pedido | Início da ajuda | Espera |
|---|---|---|---|---|
| 0 | 1 | 10,085 | 15,197 | 5,113 |
| 1 | 1 | 11,077 | 15,197 | 4,121 |
| 2 | 1 | 12,075 | 15,197 | 3,122 |
| 3 | 2 | 13,073 | 18,275 | 5,202 |
| 4 | 2 | 14,071 | 18,275 | 4,204 |
| 5 | 2 | 15,075 | 18,275 | 3,200 |

Os 3 elfos do mesmo grupo têm o **mesmo** início de ajuda (`noel.c:55-56`), então o 1º a chegar sempre espera mais. Média: 4,160 ms; máximo = p95 = 5,202 ms.

## 7. Lendo as três execuções lado a lado

| Campo | Normal (`E06_R10`) | Teste | Ingênua | O que a diferença mostra |
|---|---|---|---|---|
| `status` | ok | ok | **violacao** | o verificador pega a inversão |
| `T` | 21,3 ms | 41,4 ms | 41,3 ms | nos testes as renas chegam em 30 ms e Noel espera por elas |
| `resposta_renas` | 0,016 ms | 0,023 ms | **6,172 ms** | a política ingênua faz as renas esperarem 2 ajudas |
| `espera_p95` | 5,2 ms | 25,3 ms | 20,1 ms | nos testes os elfos ficam parados até 30 ms; a ingênua os atende antes |
| `viol_prio` | 0 | 0 | **2** | 2 decisões erradas |
| `viol_regras` | 0 | 0 | 0 | o resto da sincronização está correto nas três |
| `decisoes (disputa)` | 3 (0) | 3 (1) | 3 (2) | a normal **não** testa a prioridade |
| `util_noel` | 52,5% | 27,1% | 27,1% | mesmo trabalho (≈ 11 ms) dividido por um T maior |

**A ordem das decisões** (coluna `evento = decisao` do `eventos.csv`):

| | 1ª decisão | 2ª | 3ª |
|---|---|---|---|
| Normal | renas (10,114; só as renas e 1 elfo prontos) | grupo 1 | grupo 2 |
| Teste | **renas** (30,135; disputa) | grupo 1 | grupo 2 |
| Ingênua | **grupo 1** (30,101; disputa → violação) | **grupo 2** (33,182; disputa → violação) | renas (36,263) |

A diferença entre a linha "Teste" e a linha "Ingênua" vem inteira de `noel.c:117`. Nas duas, as threads, o mutex, as variáveis de condição e os horários de chegada são os mesmos.

## 8. O que a saída não prova

- **`viol_prio=0` sem disputa não prova a prioridade.** Nas 25 execuções da matriz, `com disputa` foi sempre 0 (`dados/log_execucao.txt`) [CONFIRMADO 2026-10-28]. A prioridade só é testada no teste de prioridade e na ingênua.
- **Os verificadores medem as regras que o código conhece.** Eles leem o estado sob o mutex no instante da decisão. Uma corrida que corrompesse um contador sem violar nenhuma das regras da tabela 3.9 não apareceria. A ausência de corrida se apoia na análise do código e no estresse (300 execuções sem falha); ThreadSanitizer e Helgrind não puderam ser usados nesta máquina (ver [[Execução e Flags (Papai Noel)]]).
- **Uma execução é uma amostra.** A ordem das threads muda entre execuções. Por isso o experimento repete cada configuração 5 vezes, e o estresse, 100 vezes.
- **Os tempos são da máquina e do momento.** A vazão e as esperas dependem do escalonador; compare tendências, não o terceiro dígito.

## 9. Fala pronta para a apresentação

> "A linha de resumo só é impressa depois que todas as threads terminam, para não atrapalhar a medição. Durante a simulação, cada thread só anota instantes e contadores, sempre com o mutex. Os campos de violação são verificadores: no momento da decisão, Noel olha os mesmos predicados que usou para decidir e conta se escolheu elfos com as nove renas prontas. Mas `viol_prio=0` só significa algo quando há disputa. Por isso o campo `com disputa` existe, e o teste de prioridade obriga a primeira decisão a ter disputa. A versão ingênua, que muda só uma linha, dá `viol_prio=2` e a resposta às renas sobe de 0,02 para 6 ms: o verificador detecta o erro."

Perguntas prováveis:

- **"Por que a resposta às renas não é zero?"** É o tempo de Noel acordar do `pthread_cond_wait`, readquirir o mutex (que a rena acabou de soltar) e decidir. São microssegundos de escalonamento.
- **"Por que p95 igual ao máximo?"** Com 6 amostras, ⌈0,95·6⌉ = 6, a última posição. Com 12 elfos, ⌈11,4⌉ = 12 também. O p95 só se separa do máximo a partir de 20 amostras.
- **"Como vocês sabem que não contaram uma violação a mais?"** O contador fica dentro da seção crítica da decisão (`noel.c:111-119`) e só é lido depois dos joins.
