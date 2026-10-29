# Tema 11 — Problema do Papai Noel (C11 + pthreads)

Atividade de Sistemas Operacionais (Prof. Lucca Abbado Neres, FAG): implementação, experimentos e apresentação de um problema de sincronização.

**Integrantes:** [Integrante 1] · [Integrante 2] · [Integrante 3]

## O que é

Noel dorme até ser acordado por um grupo de **exatamente 3 elfos** ou pela chegada das **9 renas**. Se as duas demandas estão prontas ao mesmo tempo, as renas têm prioridade. Esta é a versão finita: há uma única viagem e cada elfo faz um único pedido. Depois da viagem, Noel atende os grupos restantes e o programa encerra.

- 1 thread Noel, 9 threads rena e N threads elfo, todas criadas antes de qualquer `pthread_join`.
- Um único `pthread_mutex_t` e quatro `pthread_cond_t`: largada, Noel, elfos e renas. A de Noel usa `CLOCK_MONOTONIC` e `timedwait` para o timeout de segurança.
- Os grupos são uma **fila com ids**. O 3º elfo fecha o grupo na mesma seção crítica em que se inscreve e avança `grupo_aberto`, então nenhum elfo invade um grupo fechado.
- Não há espera ocupada. Os sleeps (`clock_nanosleep` absoluto) servem apenas para simular a chegada (elfo *i* chega em 10 + *i* ms), a ajuda (3 ms) e a preparação (5 ms).
- As invariantes são verificadas em tempo de execução: grupo com ≠ 3 elfos, viagem com < 9 renas, prioridade violada, decisão durante uma ajuda, elfo atendido 0 ou 2+ vezes e invasão de grupo.
- Os eventos ficam em memória e são exportados para CSV só depois dos joins.

## Dependências

- `gcc` com suporte a C11 e pthreads (testado com GCC 15.3.1, glibc 2.42, Fedora 43)
- Python 3 com `pandas` e `matplotlib`, para os gráficos
- Opcional, para regenerar o relatório e os slides: `reportlab`, `python-pptx` e as fontes Liberation

```bash
python3 -m pip install pandas matplotlib reportlab python-pptx
```

## Compilação

```bash
cd src
gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao     # compila sem warnings
```

## Execução

```bash
./simulacao --elfos 6 --renas-ms 10 --rep 1 --semente 11 --out ../dados/
./simulacao --elfos 6 --renas-ms 30 --out ../dados/teste_prioridade/ --teste-prioridade
```

| Argumento | Significado | Padrão |
|---|---|---|
| `--elfos N` | quantidade de elfos, múltiplo de 3 (3..300) | obrigatório |
| `--renas-ms R` | instante em que as 9 renas chegam (ms após o sinal de início) | obrigatório |
| `--rep K` | número da repetição, gravado nos CSVs | 1 |
| `--semente S` | id registrado da repetição (o programa **não** usa aleatoriedade) | 11 |
| `--out DIR` | pasta onde `resumo.csv`, `eventos.csv` e `espera_elfos.csv` são **acrescentados** | `dados/` |
| `--timeout-ms MS` | timeout de segurança: grava status `timeout` em vez de travar | 2000 |
| `--teste-prioridade` | Noel só é liberado quando as renas **e** um grupo estão prontos; imprime as verificações e sai com 0 se passar | — |
| `--ingenua` | política ingênua (elfos antes das renas), só para demonstrar a violação | — |
| `--ajuda-ms`, `--preparo-ms`, `--elfo0-ms` | durações (ajuda, preparação, chegada do elfo 0) | 3, 5, 10 |

Códigos de saída: 0 = ok; 2 = timeout ou violação; 1 = erro, ou teste de prioridade que falhou; 64 = argumentos inválidos.

## Experimentos e gráficos

```bash
bash scripts/run_experimentos.sh        # compila; piloto; 25 execuções; teste funcional; ingênua; estresse
python3 scripts/graficos.py             # G1..G4 em graficos/ e dados/tabela_esperas.csv
python3 scripts/gerar_relatorio.py      # relatorio.pdf (números lidos dos CSVs)
python3 scripts/gerar_slides.py         # slides.pptx
```

A matriz tem 5 configurações × 5 repetições (sementes 11, 22, 33, 44, 55): a referência (6 elfos, renas em 10 ms), o conjunto 1 (3, 6 e 12 elfos com renas em 10 ms) e o conjunto 2 (renas em 5, 10 e 30 ms com 6 elfos). O script apaga os CSVs da rodada anterior antes de começar.

## Estrutura

```
Problema_Papai-Noel/
├── src/        main.c noel.c elfo.c rena.c metricas.c csv.c tempo.c + comum.h e headers
├── scripts/    run_experimentos.sh, graficos.py, gerar_relatorio.py, gerar_slides.py
├── dados/      resumo.csv, eventos.csv, espera_elfos.csv, tabela_esperas.csv, ambiente.txt,
│               log_execucao.txt, compilacao.txt, teste_prioridade/, ingenua/, piloto/, estresse/
├── graficos/   G1_vazao_elfos.png, G2_p95_renas.png, G3_p95_grupo.png, G4_linha_tempo.png
├── apresentacao/        apresentacao_papai_noel.pptx (v4) e gerar_apresentacao.py
├── papai_noel_infinito/ versão com ciclos infinitos e interface web (README próprio)
├── vault/               notas do Obsidian
├── relatorio.pdf
└── README.md
```

## CSVs

- **`resumo.csv`** (uma linha por execução): `tema, configuracao, conjunto, repeticao, semente, elfos, renas_ms, T_ms` (do sinal de início ao encerramento de Noel), `previstos, concluidos` (pedidos de elfos), `vazao_pedidos_s` (= concluidos / (T_ms/1000)), `espera_media_ms, espera_p95_ms, espera_max_ms` (do pedido ao início da ajuda; o p95 é a posição ⌈0,95·n⌉ da lista ordenada, ou `N/A` sem amostras), `n_amostras`, `resposta_renas_ms` (da 9ª rena ao início da preparação), `violacoes_prioridade, violacoes_regras`, `utilizacao_noel` (fração de T em ajuda ou preparação) e `status` (`ok`, `timeout` ou `violacao`).
- **`eventos.csv`**: `execucao, t_ms, participante, tipo` (`noel`, `elfo` ou `rena`), `evento` (`chegada`, `grupo_pronto`, `nona_rena`, `decisao`, `inicio_ajuda`, `fim_ajuda`, `inicio_preparacao`, `fim_preparacao`, `encerramento` ou `timeout`), `estado_noel` (logo após o evento) e `grupo_id` (vazio na viagem). Na `decisao`, `grupo_id` vazio significa "renas".
- **`espera_elfos.csv`**: `execucao, elfo_id, grupo_id, t_pedido_ms, t_inicio_ajuda_ms, espera_ms`.
- **`tabela_esperas.csv`**: resumo por configuração (média, p95 e máximo das esperas, vazão, resposta às renas, taxa de execuções válidas), gerado por `graficos.py`.

## Resultados (rodada incluída)

25/25 execuções válidas e zero violações. Vazão de 163 → 281 → 436 pedidos/s para 3 → 6 → 12 elfos. O p95 da espera é ≈ 5,2 ms com as renas junto e ≈ 2,1 ms antes ou depois. O teste de prioridade **passou**, e a política ingênua gerou 2 violações. Veja `relatorio.pdf` para a análise.

## Referências

- A. B. Downey, *The Little Book of Semaphores*, seção "The Santa Claus problem" (formulação clássica; não copiamos código, a solução com fila de grupos e cond vars é nossa).
- J. A. Trono, "A new exercise in concurrency", *SIGCSE Bulletin* 26(3), 1994 (origem do problema).
- Páginas de manual POSIX: `pthread_cond_timedwait(3p)`, `pthread_condattr_setclock(3p)`, `clock_nanosleep(2)`.
- Nenhum trecho de código foi adaptado de fontes externas.
