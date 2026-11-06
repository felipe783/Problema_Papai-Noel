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
Codigo: "Problema_Papai-Noel"
Repositorio: "https://github.com/felipe783/Problema_Papai-Noel"
Atualizado: 2026-10-29
---
# Papai-Noel

Trabalho de **Sistemas Operacionais** (Tema 11, Prof. Lucca Abbado Neres, FAG): o **Problema do Papai Noel** em **C11 com pthreads**, na versão finita. São uma thread Noel, 9 renas e N elfos. Noel atende grupos de exatamente 3 elfos e prepara uma única viagem quando as 9 renas chegam, com prioridade para as renas. O programa mede vazão, espera dos elfos e resposta às renas em 25 execuções, e scripts Python geram os gráficos, o relatório e os slides.

- **Código:** `src/` na raiz do projeto (7 arquivos `.c` e os headers). Até 2026-10-28 tudo ficava em `tema11_papai_noel/`; em 2026-10-29 o conteúdo passou para a raiz, sem mudar o código (os arquivos de `src/` são de 2026-10-28 10:05). Por isso as referências `arquivo:linha` das notas continuam valendo: as 1342 foram conferidas contra o tamanho dos arquivos em 2026-10-29 [CONFIRMADO 2026-10-29]. A documentação fica em `vault/`.
- **Entrada:** argumentos de linha de comando (`--elfos`, `--renas-ms`, `--rep`, `--semente`, `--out`, `--teste-prioridade`, `--ingenua`, `--timeout-ms`).
- **Saída:** `resumo.csv`, `eventos.csv` e `espera_elfos.csv` em `dados/`, os PNGs G1–G4 em `graficos/`, mais `relatorio.pdf` e a apresentação.
- **Apresentação (v4, 2026-10-28, atual):** `apresentacao/apresentacao_papai_noel.pptx`. O gerador produz 27 slides + 4 de apoio em 6 seções com page tracker, mas o arquivo atual foi editado à mão e tem **22 slides** [CONFIRMADO 2026-10-29] (correspondência em [[Guia da Apresentação v4 (Papai Noel)#Correspondência com o deck atual (22 slides)]]). Ele é gerada por `apresentacao/gerar_apresentacao.py` (código lido de `src/`, números de `dados/`). Planejada com as skills de apresentação (pirâmide + SCQA, títulos de ação, um acento por slide). Roteiro e estudo slide a slide em [[Guia da Apresentação v4 (Papai Noel)]].
- **Versões anteriores dos slides:** a v3 (37 slides, `scripts/gerar_slides.py`) não tem mais o `slides.pptx` na pasta [CONFIRMADO 2026-10-28], mas o script ainda o regenera; seu guia é [[Guia Completo da Apresentação (Papai Noel)]]. A v1 (10 slides) e a v2 (36) estão em `backup/`.
- **Versão infinita com interface web (2026-10-28):** pasta `papai_noel_infinito/`, ao lado da finita (que fica na raiz) no GitHub `felipe783/Problema_Papai-Noel`. Ciclos sem fim, relógio virtual com pausa/velocidade e interface servida por `servidor.py` (`make web`). Detalhes em [[Versão Infinita com Interface (Papai Noel)]].
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
| Matriz de 25 execuções + gráficos | 25/25 `ok` nas duas rodadas (10:08, a dos slides, em `dados_backup/`; e 21:22, em `dados/`) [CONFIRMADO 2026-10-29] |
| Versão infinita + interface web (`papai_noel_infinito/`) | Implementada; estresse com 0 violações [CONFIRMADO 2026-10-28] |
| Testes automatizados com sanitizers (TSan/Helgrind) | Não existem: as ferramentas não estão instaladas na máquina |

## Como rodar

```bash
cd src
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

Caminhos de arquivo citados nas notas partem da raiz do projeto `Problema_Papai-Noel/`. Os números medidos são da rodada que está nos slides ([[Testes e Gráficos (Papai Noel)#Duas rodadas de dados]]).

### Ordem de estudo

| Passo | Objetivo | Onde estudar |
|---|---|---|
| 1 | Entender o problema: atores, regras, prioridade, grupos de 3 | [[Lógica e Fluxo (Papai Noel)]] (regras e estados); [[Guia de Estudo Teórico (Papai Noel)]], cap. 6 |
| 2 | Conceitos de concorrência: thread, escalonamento, seção crítica, condição de corrida, mutex, semáforo, variável de condição | [[Guia de Estudo Teórico (Papai Noel)]], cap. 1 a 4 |
| 3 | Por que uma solução ingênua falha | Sem exclusão mútua (`if` com contador, só teoria): [[Guia de Estudo Teórico (Papai Noel)]], cap. 5, e [[Sincronização no Código (Papai Noel)#2.7 O que daria errado sem o mutex ou com uso incorreto]]. Com a regra de decisão invertida (`--ingenua`, medida): [[Evidências nos Dados (Papai Noel)#6. Evidência 5: correta × ingênua]] |
| 4 | A solução implementada, do `main` ao último `join` | [[Fluxo do Código e Sincronização (Papai Noel)]], [[Laços do Código (Papai Noel)]] e [[Guia da Pasta src (Papai Noel)]] |
| 5 | O papel de cada mecanismo: onde nasce, quem espera, quem avisa, o que protege | [[Sincronização no Código (Papai Noel)]] (**nota técnica principal**; semáforos não são usados: seção 3) |
| 6 | Métricas, experimentos e gráficos | [[Testes e Gráficos (Papai Noel)]] (números), [[Interpretação dos Gráficos (Papai Noel)]] (leitura), [[Evidências nos Dados (Papai Noel)]] (tabelas), [[Saída do Programa (Papai Noel)]] (campos) |
| 7 | Resultados, garantias e limitações: o que é provado pelo código e o que só foi observado | [[Riscos de Sincronização (Papai Noel)]]; [[Evidências nos Dados (Papai Noel)#9. Conclusões: observado, garantido e limites]]; [[Fluxo do Código e Sincronização (Papai Noel)#6. O que é garantido e o que não é]] |
| 8 | Responder ao professor | [[Perguntas da Apresentação (Papai Noel)]], [[Mapa de Perguntas por Slide (Papai Noel)]], [[Guia da Apresentação v4 (Papai Noel)]] e, na véspera, [[RESUMO_REVISAO_RAPIDA]] |

Com pouco tempo: [[Guia da Apresentação v4 (Papai Noel)]] → [[Sincronização no Código (Papai Noel)]] → [[Perguntas da Apresentação (Papai Noel)]] → [[Interpretação dos Gráficos (Papai Noel)]]; na véspera, [[RESUMO_REVISAO_RAPIDA]].

### Onde está cada pergunta do professor

As mesmas perguntas aparecem em várias notas, com finalidades diferentes. Para fatos do código (linhas, nomes, quantidade de mecanismos), a referência é [[Perguntas da Apresentação (Papai Noel)]] e [[Sincronização no Código (Papai Noel)]].

| Para quê | Nota | Onde |
|---|---|---|
| Resposta oral + aprofundamento + código + pergunta extra (15 perguntas: as 8 do professor e 7 sobre o código) | [[Perguntas da Apresentação (Papai Noel)]] | seções 1 a 15 |
| Resposta curta em tabela, para revisar | [[RESUMO_REVISAO_RAPIDA]] | seção 7 |
| Em que slide responder cada uma | [[Mapa de Perguntas por Slide (Papai Noel)]] | "As perguntas do professor e onde respondê-las" |
| Base teórica de cada resposta (escrita sobre uma implementação de referência) | [[Guia de Estudo Teórico (Papai Noel)]] | 12.3 a 12.10 |
| Respostas em 4 níveis (v3, histórico) | [[Guia Completo da Apresentação (Papai Noel)]] | [[Guia Completo da Apresentação (Papai Noel)#Parte 5. As perguntas do professor]] |

### `Apresentacao/`: preparar e defender a apresentação

- [[Guia da Apresentação v4 (Papai Noel)]]: **guia principal, roteiro da v4** (31 slides; o deck atual tem 22, com tabela de correspondência no início): para cada slide, objetivo, conceitos, fala, visuais, código, perguntas e erros a evitar; fundamentos, fluxo de ponta a ponta com Mermaid, banco de perguntas e checklist.
- [[Mapa de Perguntas por Slide (Papai Noel)]]: **cola rápida da v4**: fluxo Mermaid dos slides, com o que explicar e quais perguntas responder em cada um.
- [[Perguntas da Apresentação (Papai Noel)]]: as 15 perguntas, cada uma com resposta oral, explicação, exemplo do código e pergunta extra do professor.
- [[RESUMO_REVISAO_RAPIDA]]: **revisão rápida** de todo o trabalho (visão geral, conceitos, código, fluxo, perguntas, gráficos, pegadinhas e uma revisão de um minuto).
- `Historico/` → [[Guia Completo da Apresentação (Papai Noel)]]: guia da **v3** (37 slides), substituído pela v4. Continua valendo como aprofundamento: fundamentos de SO, as 8 perguntas do professor em 4 níveis, gráficos, propriedades e simulação de defesa. Os números de slide dele não valem para a v4.

### `Codigo/`: como o programa funciona

- [[Sincronização no Código (Papai Noel)]]: **a nota técnica principal**. Cobre o mutex, cada variável de condição, a ordem das operações e o que acontece em ordens diferentes.
- [[Guia da Pasta src (Papai Noel)]]: cada arquivo de `src/` em blocos (responsabilidade, o que faz, relação com o problema, o que falharia), estruturas de dados e dependências entre módulos.
- [[Fluxo do Código e Sincronização (Papai Noel)]]: a execução **fase a fase** (largada, elfos, grupo, renas, decisão, ajuda, viagem, encerramento), os cinco papéis da sincronização e os cenários de chegada das renas.
- [[Lógica e Fluxo (Papai Noel)]]: regras, estados de Noel, transições e linhas do tempo reais de cada cenário.
- [[Laços do Código (Papai Noel)]]: **a lógica dos laços em Mermaid** (visão geral, laço do Noel, esperas dos elfos e das renas), sem linhas de código.
- [[Riscos de Sincronização (Papai Noel)]]: corrida, aviso perdido, deadlock, starvation etc., separando erros comprovados de riscos teóricos.
- [[Versão Infinita com Interface (Papai Noel)]]: a variação com ciclos infinitos, relógio virtual e interface web (`papai_noel_infinito/`); diferenças em relação à versão finita.

### `Execucao/`: rodar, ler a saída e interpretar os resultados

- [[Execução e Flags (Papai Noel)]]: pré-requisitos, compilação, execução, **todas as flags** com validações e códigos de saída, testes, experimentos, gráficos, limpeza e erros comuns.
- [[Saída do Programa (Papai Noel)]]: cada campo da linha de resumo, das linhas `[teste-prioridade]` e dos 3 CSVs, ligado à linha de código onde nasce, com as execuções normal, teste e ingênua comparadas.
- [[Testes e Gráficos (Papai Noel)]]: método, números, as **duas rodadas de dados** e como apresentar G1–G4.
- [[Evidências nos Dados (Papai Noel)]]: **o que é cada arquivo de `dados/`** e cada verificação avulsa, com **tabelas prontas para mostrar**: renas em fila no mutex, quando o Noel segura o mutex, uso de CPU, matriz, correta × ingênua, testes de sensibilidade, robustez e conclusões (observado × garantido × limites).
- [[Interpretação dos Gráficos (Papai Noel)]]: **como ler e defender cada gráfico** (G1–G4 e as linhas do tempo dos slides): inventário real × conceitual × hipotético, método de leitura, ligação com o código, o que comprova e o que não comprova, perguntas, roteiro oral, melhorias sugeridas e 10 exercícios.

### `Teoria/`: conceitos, independente do código

- [[Guia de Estudo Teórico (Papai Noel)]]: guia teórico escrito **sem** o código do grupo. Usa uma implementação de referência, com 3 cond vars e outros nomes; no início há uma tabela que a compara com o código real. Vale para a teoria, não para detalhes do código.

### Referências

As fontes bibliográficas (Trono 1994, a proposta original do problema; Ben-Ari 1998; Downey, *The Little Book of Semaphores*; OSTEP; Silberschatz; Tanenbaum; POSIX) estão em [[Guia de Estudo Teórico (Papai Noel)#13. Referências]]. Elas foram listadas de memória, sem consulta, e é preciso conferir edição e páginas antes de citá-las no relatório [NÃO VERIFICADO]. Os dois links gratuitos (OSTEP e Downey) responderam em 2026-10-29 [CONFIRMADO 2026-10-29].

## Problemas conhecidos

- [CONFIRMADO 2026-10-28] Os retornos de `pthread_mutex_init`/`pthread_cond_init` (`main.c:131-139`) não são verificados. Na prática não falham com atributos padrão, mas um avaliador rigoroso pode apontar isso.
- [CONFIRMADO 2026-10-28] Se `pthread_create` falhar no meio (`main.c:187-204`), `main` retorna sem fazer os joins. O processo termina e as threads já criadas morrem junto, sem travar, mas sem limpeza. Além disso, o erro é reportado com `perror`, mas `pthread_create` devolve o código de erro e não usa `errno`: a mensagem pode ser enganosa. O certo seria `strerror(rc)` com o valor devolvido.
- [PROVÁVEL 2026-10-28] Se `pthread_cond_timedwait` devolvesse um erro diferente de `ETIMEDOUT` (por exemplo `EINVAL`), `noel.c:107` voltaria ao laço e o Noel giraria sem dormir. Com os argumentos atuais isso não acontece.
- [CONFIRMADO 2026-10-28] `--timeout-ms` só é verificado enquanto Noel espera sem trabalho: não limita a duração total (T = 215 ms com `--ajuda-ms 100 --timeout-ms 50`, status `ok`). No timeout, threads em sleep de chegada não são interrompidas, e o processo só termina quando elas acordam.
- [CONFIRMADO 2026-10-28] `--out` precisa apontar para uma pasta existente; senão a simulação roda, mas o programa sai com código 1 sem gravar os CSVs. `graficos.py` sempre regrava `tabela_esperas.csv` na pasta de `--dados`, mesmo com `--saida` em outro lugar.
- [CONFIRMADO 2026-10-28] Os slides 16 e 31 da v4 usam números digitados em `gerar_apresentacao.py` (`R13`, `EMPATE`), de execuções avulsas cujo CSV não foi salvo em `dados/`. Reexecutadas, a ordem dos eventos se repete, mas o empate deu 10/30 (o slide diz 12/30). Sugestão: salvar em `dados/extra/` e ler de lá ([[Interpretação dos Gráficos (Papai Noel)]], seção 10).
- [CONFIRMADO 2026-10-29] O `.pptx` atual tem 22 slides, editados à mão: saíram o método (v4 21), os testes (26), a conclusão (27) e os 4 de apoio. Os guias seguem a numeração da v4, e rodar `gerar_apresentacao.py` desfaz a edição. A tabela de correspondência está no [[Guia da Apresentação v4 (Papai Noel)]].
- [CONFIRMADO 2026-10-29] Os slides e as notas usam a rodada das 10:08 (`dados_backup/`, `graficos_backup/`), mas `dados/` e `graficos/` têm a rodada das 21:22. `dados/log_execucao.txt` ainda é o das 10:08. Ver [[Testes e Gráficos (Papai Noel)#Duas rodadas de dados]].
- [CONFIRMADO 2026-10-29] O slide 1 e `gerar_apresentacao.py:383` ainda mostram o caminho antigo `tema11_papai_noel/src`.
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
   - [CONFIRMADO 2026-10-28] Na matriz das 10:08, nenhuma decisão teve disputa (`com disputa: 0` em `log_execucao.txt`): a prioridade é exercitada só pelo teste funcional e pela ingênua. Vale dizer isso nos slides de resultados (eram os slides 24/35 da v3).
2. Decidir qual rodada apresentar. Para manter os slides, use os números de `dados_backup/`. Para usar a de `dados/`, regenere o deck (isso recria os 31 slides) e confira as falas.
3. Atualizar o caminho do slide 1 (`gerar_apresentacao.py:383`) e os `[Integrante 1/2/3]` do `README.md` e do `relatorio.pdf`.
