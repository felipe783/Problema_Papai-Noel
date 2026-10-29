# Problema do Papai Noel — versão infinita com interface

Variação do Tema 11 (Sistemas Operacionais) em que Noel, renas e elfos repetem seus ciclos **para sempre**, com uma interface web que mostra o estado em tempo real. A versão finita do trabalho fica na raiz do repositório (`../`) e não foi alterada.

- **Noel** dorme até haver as **9 renas** no estábulo ou um **grupo de 3 elfos** na fila. Com os dois prontos, as **renas têm prioridade**. Depois ele atrela o trenó, viaja (e nesse tempo não atende ninguém) e volta a dormir.
- **Renas:** férias (tempo sorteado) → estábulo → viagem → férias...
- **Elfos:** trabalho (tempo sorteado) → pedem ajuda → grupo de 3 → fila → são ajudados → trabalho...

## Sincronização (C11 + pthreads)

| Recurso | Para quê |
|---|---|
| `mutex` (1) | protege todo o estado da oficina |
| `cv_noel` | Noel dorme até `renas == 9` ou haver grupo fechado na fila |
| `cv_renas` | as renas esperam `viagens_concluidas >= minha_viagem` |
| `cv_elfos` | cada elfo espera `ultimo_concluido >= meu_grupo` |

- Grupos são uma **fila com ids crescentes** (anel de 32 posições). O 3º elfo fecha o grupo na mesma seção crítica em que se inscreve, então ninguém invade grupo fechado. Noel atende em ordem FIFO.
- Toda espera é sobre um **predicado** num laço `while`, então acordar espúrio e aviso perdido não causam erro.
- Sem semáforos e sem espera ocupada. Os sleeps só simulam durações.
- **Relógio virtual** (`relogio.c`, mutex próprio): a pausa e a velocidade atuam dentro da simulação em C, não só na animação. A ordem de locks é sempre `oficina → relógio`.
- Invariantes conferidas em tempo de execução: viagem sem 9 renas, grupo com ≠ 3 elfos, ajuda com as 9 renas esperando (prioridade violada), estouro do anel de grupos. O contador `violacoes` deve ficar em 0.
- Encerramento limpo: `SIGINT`/`SIGTERM` são tratados por uma thread com `sigwait`; o comando `sair` ou EOF no stdin também encerram. Todas as threads de atores recebem `join` e o resumo sai em stderr.

## Como rodar

Requisitos: `gcc` com C11/pthreads e Python 3 (só a biblioteca padrão).

```bash
cd papai_noel_infinito
make web          # compila e abre o servidor em http://127.0.0.1:8000
```

Abra **http://127.0.0.1:8000**. A simulação começa sozinha. Pela interface dá para reiniciar, pausar, parar, mudar a velocidade (0,5× a 16×) e ajustar os parâmetros. O servidor recompila o binário sozinho se o código C mudar. Para outra porta: `python3 servidor.py --porta 8080`.

Também roda só no terminal:

```bash
make run                                         # texto legível, velocidade 4×, Ctrl+C mostra o resumo
./src/noel_infinito --texto --duracao-s 120 --elfos 12
```

Com a simulação rodando no terminal, dá para digitar `p` (pausar), `r` (retomar), `v 8` (velocidade) e `q` (sair).

| Opção | Significado | Padrão |
|---|---|---|
| `--elfos N` | quantidade de elfos (3..60) | 10 |
| `--ferias MIN MAX` | férias de cada rena, em ms | 5000 10000 |
| `--trabalho MIN MAX` | trabalho do elfo até pedir ajuda, em ms | 3000 12000 |
| `--ajuda MS` | duração de uma ajuda | 1200 |
| `--preparo MS` | tempo para atrelar o trenó | 1000 |
| `--viagem MS` | duração da viagem | 3000 |
| `--semente S` | semente dos sorteios (`rand_r`, uma por thread) | 42 |
| `--velocidade V` | ms virtuais por ms real (0,1..50) | 1 |
| `--duracao-s S` | encerra após S segundos virtuais (0 = infinito) | 0 |
| `--texto` | saída legível em vez de JSON | — |

Códigos de saída: 0 = ok, 2 = houve violação de invariante, 64 = argumentos inválidos.

## Arquitetura

```
navegador (web/)  ◄── SSE /api/eventos ──  servidor.py  ◄── stdout (JSON Lines) ──  src/noel_infinito
                  ──► POST /api/...    ──►              ──► stdin (pausar, retomar, velocidade V, sair)
```

- Cada linha JSON traz o evento **e o estado completo** (Noel, 9 renas, N elfos, grupo aberto, fila, métricas). A interface só desenha a última linha, e quem conecta no meio da execução se sincroniza na hora (o servidor reenvia as últimas 200 linhas).
- Rotas: `GET /api/estado`, `GET /api/eventos`, `POST /api/iniciar` (parâmetros em JSON), `/api/pausar`, `/api/retomar`, `/api/velocidade` (`{"v": 4}`), `/api/parar`.
- Se o servidor morrer, o processo C recebe EOF no stdin e encerra sozinho.

## Estrutura

```
papai_noel_infinito/
├── src/        main.c noel.c rena.c elfo.c relogio.c saida.c + comum.h, atores.h, relogio.h, saida.h
├── web/        index.html, style.css, app.js (sem dependências externas)
├── servidor.py
├── Makefile
└── README.md
```

## Métricas da interface

- **Espera dos elfos:** do pedido de ajuda ao início da ajuda (média e máximo). O gráfico mostra cada elfo atendido; os picos coincidem com as viagens.
- **Resposta às renas:** da chegada da 9ª rena ao início do preparo. Fica acima de zero quando Noel estava no meio de uma ajuda, que nunca é interrompida.
- **Utilização do Noel:** fração do tempo em ajuda, preparo ou viagem.
- **Disputas:** decisões em que renas e grupo estavam prontos ao mesmo tempo. Em todas, as renas venceram.

## Verificação (2026-10-28, Fedora 43, GCC 15.3.1)

- Compila sem warnings com `-std=c11 -O2 -Wall -Wextra -pthread`.
- Estresse com 60 elfos, tempos curtos e velocidade 50× por 300 s virtuais: 3.628 viagens, 19.800 grupos, 3.628 disputas (todas vencidas pelas renas), **0 violações**, sem travar.
- Pausa (nenhum evento durante a pausa), velocidade, reinício e parada testados pelo servidor; matar o servidor com `kill -9` encerra o processo C.
- ThreadSanitizer/Helgrind não foram rodados (não instalados na máquina).
