# Versão Infinita com Interface (Papai Noel)

Variação do trabalho em `Problema_Papai-Noel/papai_noel_infinito/`, separada da versão finita (`tema11_papai_noel/`, que não foi alterada e fica fora do Git via `.git/info/exclude`). Noel, renas e elfos repetem seus ciclos até o encerramento, e uma interface web mostra o estado ao vivo. Criada em 2026-10-28; o uso está no `README.md` da pasta. É o único código versionado em https://github.com/felipe783/Problema_Papai-Noel.

> Referências de código são de `papai_noel_infinito/src/`, conferidas em 2026-10-28.

## O que muda em relação à versão finita

| Aspecto | Finita ([[Sincronização no Código (Papai Noel)]]) | Infinita |
|---|---|---|
| Ciclos | 1 viagem, 1 pedido por elfo | renas e elfos em laço; Noel em laço até `encerrar` |
| Variáveis de condição | 4 (`cv_largada`, `cv_noel`, `cv_elfos`, `cv_renas`) | 3: sem largada comum; `cv_noel` sem `timedwait` |
| Estados de Noel | dormindo, ajudando, preparando | + **viajando** (fora de casa: a fila de elfos cresce) |
| Grupos | vetor de N/3 grupos | **anel** de 32 grupos com ids crescentes (`GRUPO(o, id)`) |
| Tempo | `clock_nanosleep` absoluto | **relógio virtual** (`relogio.c`) com pausa e velocidade |
| Chegadas | determinísticas (elfo *i* em 10 + *i* ms) | sorteadas com `rand_r`, uma semente por thread |
| Saída | 3 CSVs depois dos joins | JSON Lines em tempo real, cada linha com o estado completo |
| Encerramento | fim natural ou timeout | `SIGINT`/`SIGTERM` (thread com `sigwait`), comando `sair`, EOF no stdin ou `--duracao-s` |

## Predicados de espera

- **Noel:** dorme enquanto `renas_estabulo < 9` e `proximo_grupo == grupo_aberto` (fila vazia). Ao acordar, as renas vencem se estiverem prontas (`noel.c`, `thread_noel`).
- **Rena:** guarda `minha_viagem = viagens_concluidas + 1` ao chegar e espera `viagens_concluidas >= minha_viagem`. Nenhuma rena volta durante a viagem, porque todas as 9 estão nela.
- **Elfo:** espera `ultimo_concluido >= meu_grupo`. Funciona porque Noel atende em FIFO.

## Relógio virtual

`tempo = virt_base + (real − real_base) × velocidade`. A base é refeita ao pausar ou mudar a velocidade, então o tempo não salta. `relogio_dormir` dorme em fatias de 25 ms e espera numa cond var durante a pausa (sem espera ocupada). O relógio tem mutex próprio, e a ordem de locks é sempre **oficina → relógio**: `emitir` lê o relógio com o mutex da oficina adquirido, e o relógio nunca pega o da oficina.

## Interface

`servidor.py` (só biblioteca padrão) lança o binário, lê o stdout e retransmite via SSE; os comandos vão pelo stdin. Como cada linha carrega o estado inteiro, a interface não reconstrói estado somando eventos. Arquitetura e rotas no README da pasta.

## Verificação

- [CONFIRMADO 2026-10-28] Compila sem warnings (GCC 15.3.1, `-std=c11 -O2 -Wall -Wextra -pthread`).
- [CONFIRMADO 2026-10-28] Estresse com 60 elfos, tempos de 0–50 ms e velocidade 50× por 300 s virtuais: 3.628 viagens, 19.800 grupos, 3.628 disputas vencidas pelas renas, 0 violações, sem travar.
- [CONFIRMADO 2026-10-28] Nenhum evento durante a pausa; reinício, parada e auto-início pela interface funcionam (Firefox headless); `kill -9` no servidor faz o processo C encerrar por EOF.
- Não foram rodados ThreadSanitizer nem Helgrind (não instalados), assim como na versão finita ([[Riscos de Sincronização (Papai Noel)]]).

## Limitações

- Com `--duracao-s`, a duração é em tempo **virtual**: pausas não contam.
- Velocidades altas com muitos elfos geram centenas de eventos por segundo; o log da interface guarda só os 250 últimos.
