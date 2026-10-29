---
Tipo: projeto
Projeto: Papai-Noel
Status: ativo
Stack:
  - C11
  - pthreads
  - Python
  - pandas
  - matplotlib
Codigo: "Problema_Papai-Noel/tema11_papai_noel"
Atualizado: 2026-10-29
---
# Papai-Noel

Trabalho de **Sistemas Operacionais** (Tema 11, Prof. Lucca Abbado Neres, FAG): o **Problema do Papai Noel** em **C11 com pthreads**, na versão finita. São uma thread Noel, 9 renas e N elfos. Noel atende grupos de exatamente 3 elfos e prepara uma única viagem quando as 9 renas chegam, com prioridade para as renas. O programa mede vazão, espera dos elfos e resposta às renas em 25 execuções, e scripts Python geram os gráficos, o relatório e os slides.

- **Código:** `tema11_papai_noel/src/` (7 arquivos `.c` e os headers). A documentação fica em `vault/`.
- **Entrada:** argumentos de linha de comando (`--elfos`, `--renas-ms`, `--rep`, `--semente`, `--out`, `--teste-prioridade`, `--ingenua`, `--timeout-ms`).
- **Saída:** `resumo.csv`, `eventos.csv` e `espera_elfos.csv` em `dados/`, os PNGs G1–G4 em `graficos/`, mais `relatorio.pdf` e a apresentação.
- **Apresentação (v4, 2026-10-28, atual):** `tema11_papai_noel/apresentacao/apresentacao_papai_noel.pptx`, 27 slides + 4 de apoio em 6 seções com page tracker, gerada por `apresentacao/gerar_apresentacao.py` (código lido de `src/`, números de `dados/`). Planejada com as skills de apresentação (pirâmide + SCQA, títulos de ação, um acento por slide). Roteiro e estudo slide a slide em [[Guia da Apresentação v4 (Papai Noel)]].
- **Versões anteriores dos slides:** a v3 (37 slides, `scripts/gerar_slides.py`) não tem mais o `slides.pptx` na pasta [CONFIRMADO 2026-10-28], mas o script ainda o regenera; seu guia é [[Guia Completo da Apresentação (Papai Noel)]]. A v1 (10 slides) e a v2 (36) estão em `backup/`.
- **Versão infinita com interface web (2026-10-28):** pasta `papai_noel_infinito/`. É a única versão no GitHub (`felipe783/Problema_Papai-Noel`); `tema11_papai_noel/` fica só local, ignorada via `.git/info/exclude`. Ciclos sem fim, relógio virtual com pausa/velocidade e interface servida por `servidor.py` (`make web`). Detalhes em [[Versão Infinita com Interface (Papai Noel)]].
- **Sincronização:** **1 mutex + 4 variáveis de condição**. **Não há semáforos** nem `pthread_barrier`: o sinal de início é uma "barreira caseira" feita com contador e variável de condição. Detalhes em [[Sincronização no Código (Papai Noel)]].

## Status

| Funcionalidade | Estado |
|---|---|
| Threads Noel/renas/elfos com mutex e cond vars | Implementado (`noel.c`, `rena.c`, `elfo.c`) |
| Grupos de 3 sem invasão (fila de grupos com id) | Implementado (`elfo.c:34-54`) |
| Prioridade às renas na decisão | Implementado (`noel.c:89-132`) |
| Sinal de início comum e medição com `CLOCK_MONOTONIC` | Implementado (`main.c:25-31`, `main.c:207-213`) |
| Timeout de segurança (status `timeout`) | Implementado (`noel.c:101-106`) |
| Invariantes contadas em tempo de execução | Implementado; algumas checagens são defensivas e nunca disparam por construção ([[Riscos de Sincronização (Papai Noel)]]) |
| Teste funcional `--teste-prioridade` | Passou [CONFIRMADO 2026-10-28] |
| Matriz de 25 execuções + gráficos | 25/25 `ok` [CONFIRMADO 2026-10-28] |
| Versão infinita + interface web (`papai_noel_infinito/`) | Implementada; estresse com 0 violações [CONFIRMADO 2026-10-28] |
| Testes automatizados com sanitizers (TSan/Helgrind) | Não existem: as ferramentas não estão instaladas na máquina |

## Como rodar

```bash
cd tema11_papai_noel/src
gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao
./simulacao --elfos 6 --renas-ms 10 --rep 1 --semente 11 --out ../dados/
./simulacao --elfos 6 --renas-ms 30 --out ../dados/teste_prioridade/ --teste-prioridade

cd ..
bash scripts/run_experimentos.sh     # piloto + 25 execuções + teste + ingênua + estresse
python3 scripts/graficos.py          # requer pandas e matplotlib
```

> Rodando de dentro de `src/`, sempre passe `--out` (o padrão `dados/` é relativo ao diretório atual), e use uma pasta própria para testes manuais: os CSVs são acrescentados. O Python do sistema não tem `pandas`/`matplotlib`; use um venv (`python3 -m venv .venv && .venv/bin/pip install pandas matplotlib`). Detalhes em [[Execução e Flags (Papai Noel)]].

> Verificado em 2026-10-28 (Fedora 43, GCC 15.3.1): compila sem warnings. Na matriz, 25/25 execuções `ok`. No estresse, 300/300 `ok`. O teste de prioridade PASSOU, e a política ingênua gerou 2 violações. Os scripts Python rodaram num venv com pandas, matplotlib, reportlab e python-pptx.

## Mapa das notas

Ordem sugerida para estudar: **Apresentação v4 → Sincronização no Código → Perguntas → Interpretação dos Gráficos**; o resto é aprofundamento.

### `Apresentacao/`: preparar e defender a apresentação

- [[Guia da Apresentação v4 (Papai Noel)]]: **guia principal, roteiro da v4** (31 slides): para cada slide, objetivo, conceitos, fala, visuais, código, perguntas e erros a evitar; fundamentos, fluxo de ponta a ponta com Mermaid, banco de perguntas e checklist.
- [[Mapa de Perguntas por Slide (Papai Noel)]]: **cola rápida da v4**: fluxo Mermaid dos 31 slides, com o que explicar e quais perguntas responder em cada um.
- [[Perguntas da Apresentação (Papai Noel)]]: as 15 perguntas, cada uma com resposta oral, explicação, exemplo do código e pergunta extra do professor.
- [[Guia Completo da Apresentação (Papai Noel)]]: guia da **v3** (37 slides), substituído pela v4. Continua valendo como aprofundamento: fundamentos de SO, as 8 perguntas do professor em 4 níveis, gráficos, propriedades e simulação de defesa.

### `Codigo/`: como o programa funciona

- [[Sincronização no Código (Papai Noel)]]: **a nota técnica principal**. Cobre o mutex, cada variável de condição, a ordem das operações e o que acontece em ordens diferentes.
- [[Guia da Pasta src (Papai Noel)]]: cada arquivo de `src/` em blocos (responsabilidade, o que faz, relação com o problema, o que falharia), estruturas de dados e dependências entre módulos.
- [[Fluxo do Código e Sincronização (Papai Noel)]]: a execução **fase a fase** (largada, elfos, grupo, renas, decisão, ajuda, viagem, encerramento), os cinco papéis da sincronização e os cenários de chegada das renas.
- [[Lógica e Fluxo (Papai Noel)]]: regras, estados de Noel, transições e linhas do tempo reais de cada cenário.
- [[Laços do Código (Papai Noel)]]: **a lógica dos laços em Mermaid** (visão geral, laço do Noel, esperas dos elfos e das renas), sem linhas de código.
- [[Versão Infinita com Interface (Papai Noel)]]: a variação com ciclos infinitos, relógio virtual e interface web; diferenças em relação à versão finita.
- [[Riscos de Sincronização (Papai Noel)]]: corrida, aviso perdido, deadlock, starvation etc., separando erros comprovados de riscos teóricos.

### `Execucao/`: rodar, ler a saída e interpretar os resultados

- [[Execução e Flags (Papai Noel)]]: pré-requisitos, compilação, execução, **todas as flags** com validações e códigos de saída, testes, experimentos, gráficos, limpeza e erros comuns.
- [[Saída do Programa (Papai Noel)]]: cada campo da linha de resumo, das linhas `[teste-prioridade]` e dos 3 CSVs, ligado à linha de código onde nasce, com as execuções normal, teste e ingênua comparadas.
- [[Testes e Gráficos (Papai Noel)]]: método, números e como apresentar G1–G4.
- [[Evidências nos Dados (Papai Noel)]]: **o que é cada arquivo de `dados/`** e cada verificação avulsa, com **tabelas prontas para mostrar**: renas em fila no mutex, quando o Noel segura o mutex, uso de CPU, matriz, correta × ingênua, testes de sensibilidade, robustez e conclusões (observado × garantido × limites).
- [[Interpretação dos Gráficos (Papai Noel)]]: **como ler e defender cada gráfico** (G1–G4 e as linhas do tempo dos slides 16–18): inventário real × conceitual × hipotético, método de leitura, ligação com o código, o que comprova e o que não comprova, perguntas, roteiro oral, melhorias sugeridas e 10 exercícios.

### `Teoria/`: conceitos, independente do código

- [[Guia de Estudo Teórico (Papai Noel)]]: guia teórico escrito **sem** o código do grupo (usa uma implementação de referência com 3 cond vars e outros nomes); vale para a teoria, não para detalhes do código.

## Problemas conhecidos

- [CONFIRMADO 2026-10-28] Os retornos de `pthread_mutex_init`/`pthread_cond_init` (`main.c:131-139`) não são verificados. Na prática não falham com atributos padrão, mas um avaliador rigoroso pode apontar isso.
- [CONFIRMADO 2026-10-28] Se `pthread_create` falhar no meio (`main.c:187-204`), `main` retorna sem fazer os joins. O processo termina e as threads já criadas morrem junto, sem travar, mas sem limpeza. Além disso, o erro é reportado com `perror`, mas `pthread_create` devolve o código de erro e não usa `errno`: a mensagem pode ser enganosa. O certo seria `strerror(rc)` com o valor devolvido.
- [PROVÁVEL 2026-10-28] Se `pthread_cond_timedwait` devolvesse um erro diferente de `ETIMEDOUT` (por exemplo `EINVAL`), `noel.c:107` voltaria ao laço e o Noel giraria sem dormir. Com os argumentos atuais isso não acontece.
- [CONFIRMADO 2026-10-28] `--timeout-ms` só é verificado enquanto Noel espera sem trabalho: não limita a duração total (T = 215 ms com `--ajuda-ms 100 --timeout-ms 50`, status `ok`). No timeout, threads em sleep de chegada não são interrompidas, e o processo só termina quando elas acordam.
- [CONFIRMADO 2026-10-28] `--out` precisa apontar para uma pasta existente; senão a simulação roda, mas o programa sai com código 1 sem gravar os CSVs. `graficos.py` sempre regrava `tabela_esperas.csv` na pasta de `--dados`, mesmo com `--saida` em outro lugar.
- [CONFIRMADO 2026-10-28] Os slides 16 e 31 da v4 usam números digitados em `gerar_apresentacao.py` (`R13`, `EMPATE`), de execuções avulsas cujo CSV não foi salvo em `dados/`. Reexecutadas, a ordem dos eventos se repete, mas o empate deu 10/30 (o slide diz 12/30). Sugestão: salvar em `dados/extra/` e ler de lá ([[Interpretação dos Gráficos (Papai Noel)]], seção 10).
- Não foi possível rodar ThreadSanitizer nem Helgrind (as bibliotecas não estão instaladas). A ausência de corrida se apoia na análise do código, nas invariantes e no estresse.

## Decisões

- **Fila de grupos com id**, em vez de um contador de elfos esperando: o 3º elfo fecha o grupo na mesma seção crítica em que se inscreve, o que elimina a invasão.
- **Um único mutex** para todo o estado: simplifica o raciocínio e elimina deadlock por ordem de locks, ao custo de serializar todo acesso (aceitável com 3 a 12 elfos).
- **Variáveis de condição em vez de semáforos**: cada thread espera por um **predicado** sobre o estado (o grupo concluído, a viagem concluída), não por "fichas".
- Os sleeps (`clock_nanosleep` absoluto) servem **apenas** para simular durações. Nenhuma coordenação depende deles.

## Próximos passos

1. Preparar a fala com [[Guia da Apresentação v4 (Papai Noel)]], [[Mapa de Perguntas por Slide (Papai Noel)]] e [[Perguntas da Apresentação (Papai Noel)]].
   - Tempo da fala: os 27 slides principais da v4 cabem em ~15–18 min, mas o tempo disponível não está documentado [NÃO VERIFICADO] (a v3 citava 8 min, e as notas dela somavam ≈ 20 min). Confirmar com o professor; se forem 8–10 min, usar o plano curto da seção 6 do guia v4.
   - Integrante único: Felipe Prior Mulinari. Já está no slide 1 da v4; o `relatorio.pdf` e o README ainda têm `[Integrante 1/2/3]`.
   - [CONFIRMADO 2026-10-28] Na matriz, nenhuma decisão teve disputa (`com disputa: 0` em `dados/log_execucao.txt`): a prioridade é exercitada só pelo teste funcional e pela ingênua. Vale dizer isso nos slides de resultados (eram os slides 24/35 da v3).
2. Commitar `vault/` no repositório do projeto e rodar `python scripts/sincronizar_raiz.py` no vault. Isso só funciona depois que os arquivos estiverem no Git do projeto.
