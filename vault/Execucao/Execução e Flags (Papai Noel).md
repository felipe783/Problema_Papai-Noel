# Execução e Flags (Papai Noel)

Como preparar o ambiente, compilar, executar, testar, rodar os experimentos, gerar gráficos e limpar artefatos, mais a referência completa de **todas** as flags do programa `simulacao`. Índice: [[_Papai-Noel]]. O que cada arquivo do código faz: [[Guia da Pasta src (Papai Noel)]].

> Comandos executados em 2026-10-28 (Fedora 43, GCC 15.3.1, glibc 2.42, Python 3.14.8) [CONFIRMADO 2026-10-28]. Os testes de flags foram feitos com um binário compilado numa pasta temporária, gravando em pastas temporárias, para não alterar `dados/`.

Todos os caminhos abaixo partem da **raiz do projeto**: `Problema_Papai-Noel/tema11_papai_noel/` (onde estão `src/`, `scripts/`, `dados/`, `graficos/` e o `README.md`).

## 0. Resumo rápido

```bash
cd tema11_papai_noel/src
gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao       # compila
mkdir -p /tmp/papai                                            # pasta para testes manuais
./simulacao --elfos 6 --renas-ms 10 --out /tmp/papai/          # uma execução
./simulacao --elfos 6 --renas-ms 30 --out /tmp/papai/ --teste-prioridade   # teste funcional
cd ..
bash scripts/run_experimentos.sh                               # SOBRESCREVE dados/: rodada completa
.venv/bin/python scripts/graficos.py                           # G1–G4 (precisa de pandas/matplotlib)
```

## 1. Pré-requisitos e como verificá-los

| Ferramenta | Para quê | Como verificar | Observação |
|---|---|---|---|
| `gcc` com C11 e pthreads | compilar | `gcc --version` | testado com GCC 15.3.1 |
| glibc com POSIX 2008 | `clock_nanosleep`, `pthread_condattr_setclock` | `ldd --version` | qualquer Linux atual |
| `bash`, `awk` | `run_experimentos.sh` | `bash --version` | o script também usa `hostname`, `nproc`, `free`, `uname` (só para `ambiente.txt`) |
| Python 3 + `pandas` + `matplotlib` | `graficos.py` | `python3 -c "import pandas, matplotlib"` | **não estão instalados no Python do sistema** desta máquina [CONFIRMADO 2026-10-28] |
| `reportlab` + fontes Liberation | `gerar_relatorio.py` | `ls /usr/share/fonts \| grep liberation` | as fontes estão instaladas; o script não foi executado em 2026-10-28 |
| `python-pptx` | `gerar_slides.py` | `python3 -c "import pptx"` | não foi executado em 2026-10-28 |

No Fedora, o compilador vem do pacote `gcc` (`sudo dnf install gcc`). As bibliotecas Python ficam melhor num **ambiente virtual** dentro do projeto, sem mexer no Python do sistema:

```bash
cd tema11_papai_noel
python3 -m venv .venv                                  # cria o ambiente em .venv/
.venv/bin/pip install pandas matplotlib                # o mínimo para os gráficos
.venv/bin/pip install reportlab python-pptx            # opcional: relatório e slides
```

A receita com `pandas` e `matplotlib` foi testada numa pasta temporária e gerou os 4 PNGs [CONFIRMADO 2026-10-28]. Se preferir ativar o ambiente: `source .venv/bin/activate`, e depois use `python3` normalmente.

ThreadSanitizer (`-fsanitize=thread`) **não funciona** nesta máquina: o link falha por falta de `libtsan.so.2`. O Valgrind/Helgrind também não está instalado [CONFIRMADO 2026-10-28].

## 2. Compilar

**Diretório:** `tema11_papai_noel/src/`.

```bash
gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao
```

| Parte | Significado |
|---|---|
| `-std=c11` | usa o padrão C11 (o código usa inicializadores designados e `for (int i ...)`) |
| `-O2` | otimização normal; os tempos medidos são os do binário otimizado |
| `-Wall -Wextra` | liga os avisos; o projeto compila **sem nenhum** aviso |
| `-pthread` | compila e liga com a biblioteca de threads POSIX. Sem isso, o link pode falhar ou as funções `pthread_*` podem se comportar mal |
| `*.c` | compila os 7 arquivos juntos; é necessário porque `noel.c`, `elfo.c` e `rena.c` chamam funções definidas em `main.c` |
| `-o simulacao` | nome do executável, criado em `src/` |

Não existe `Makefile`. O `run_experimentos.sh` usa exatamente esse comando e grava as mensagens do compilador em `dados/compilacao.txt`.

Para compilar a partir da raiz do projeto sem entrar em `src/`: `gcc -std=c11 -O2 -Wall -Wextra -pthread src/*.c -o src/simulacao`.

## 3. Executar

**Diretório:** qualquer um. O que importa é que **`--out` aponte para uma pasta que já exista**. O padrão `dados/` é relativo ao diretório atual, então:

| Onde você está | Comando | Grava em |
|---|---|---|
| `src/` | `./simulacao --elfos 6 --renas-ms 10 --out ../dados/` | `dados/` do projeto |
| raiz do projeto | `./src/simulacao --elfos 6 --renas-ms 10` | `dados/` do projeto (o padrão funciona) |
| `src/` | `./simulacao --elfos 6 --renas-ms 10` | **erro**: procura `src/dados/`, que não existe → código 1 |
| qualquer lugar | `.../simulacao --elfos 6 --renas-ms 10 --out /tmp/papai/` | `/tmp/papai/` (crie antes com `mkdir -p`) |

> **Cuidado:** os CSVs são abertos em **modo de acréscimo**. Uma execução manual com `--out ../dados/` acrescenta linhas à rodada oficial, e o `graficos.py` passa a contá-las. Para experimentar, use uma pasta separada (`mkdir -p /tmp/papai && ... --out /tmp/papai/`).

### 3.1 Como ler a linha impressa no console

Exemplo real (referência, 2026-10-28):

```
E06_R10_rep1: status=ok T=21.367 ms concluidos=6/6 vazao=280.81 pedidos/s espera_p95=5.235 ms
resposta_renas=0.025 ms viol_prio=0 viol_regras=0 decisoes=3 (com disputa: 0) util_noel=52.5%
```

| Campo | Significado |
|---|---|
| `E06_R10_rep1` | nome da execução: 6 elfos, renas em 10 ms, repetição 1 (prefixos `teste_`/`ingenua_` nos modos especiais) |
| `status` | `ok`, `timeout` ou `violacao` |
| `T` | ms do sinal de início ao encerramento de Noel |
| `concluidos=6/6` | elfos atendidos / previstos |
| `vazao` | pedidos de elfos por segundo: `concluidos / (T/1000)` |
| `espera_p95` | p95 da espera dos elfos; `-1.000` = sem amostra |
| `resposta_renas` | da 9ª rena ao início da preparação; `-1.000` = a viagem não começou |
| `viol_prio`, `viol_regras` | violações contadas em tempo de execução |
| `decisoes (com disputa: k)` | decisões de Noel; *disputa* = renas e grupo prontos na mesma decisão |
| `util_noel` | fração de T com Noel ajudando ou preparando |

A linha é impressa **depois** dos joins e do CSV, fora da medição (`main.c:230-236`). Explicação detalhada de cada campo e de onde ele nasce no código: [[Saída do Programa (Papai Noel)]].

## 4. Flags e argumentos

O programa só tem **flags nomeadas**. Não há argumentos posicionais nem variáveis de ambiente: um `grep` por `getenv` em `src/` não encontra nada [CONFIRMADO 2026-10-28]. Todo argumento que não seja uma flag conhecida gera erro. O parser é `ler_args` (`main.c:75-105`), e os padrões estão em `main.c:77-78`.

### 4.1 Tabela de referência

| Flag | Valor | Padrão | Validação | Campo em `Config` | Efeito |
|---|---|---|---|---|---|
| `--elfos N` | inteiro | **obrigatória** | múltiplo de 3, entre 3 e 300 | `elfos` | cria N threads elfo e N/3 grupos |
| `--renas-ms R` | inteiro (ms) | **obrigatória** | ≥ 0 | `renas_ms` | instante em que **as 9** renas chegam |
| `--rep K` | inteiro | 1 | 0..1 000 000 | `rep` | só rotula a execução (`_rep<K>`) e a coluna `repeticao` |
| `--semente S` | inteiro | 11 | 0..1 000 000 | `semente` | só é gravada na coluna `semente`; **não há aleatoriedade** |
| `--out DIR` | texto | `dados/` | nenhuma (a pasta precisa existir) | `out` | pasta onde os 3 CSVs são **acrescentados** |
| `--timeout-ms MS` | inteiro (ms) | 2000 | ≥ 1 | `timeout_ms` | prazo absoluto `t0 + MS` para a espera de Noel |
| `--elfo0-ms X` | inteiro (ms) | 10 | 0..1 000 000 | `elfo0_ms` | o elfo *i* chega em `X + i` ms |
| `--ajuda-ms A` | inteiro (ms) | 3 | 0..1 000 000 | `ajuda_ms` | duração de cada ajuda a um grupo |
| `--preparo-ms P` | inteiro (ms) | 5 | 0..1 000 000 | `preparo_ms` | duração da preparação da viagem |
| `--teste-prioridade` | (sem valor) | desligada | — | `teste_prioridade` | Noel só começa quando renas **e** grupo estão prontos; imprime as verificações e muda o código de saída |
| `--ingenua` | (sem valor) | desligada | — | `ingenua` | inverte a prioridade (elfos primeiro), só para demonstração |
| `--help`, `-h` | (sem valor) | — | — | — | imprime o uso e sai com **64** |

Todos os valores numéricos passam por `ler_int` (`main.c:65-73`): inteiro decimal, sem texto sobrando, entre 0 e 1 000 000. Não há valores fracionários: `--ajuda-ms 2.5` é rejeitado.

### 4.2 Regras do parser

- **A ordem das flags é livre**, e uma flag repetida vale pelo **último** valor.
- `--teste-prioridade`, `--ingenua` e `--help` são testadas antes de se exigir valor, então podem aparecer em qualquer posição, inclusive no fim.
- Toda outra flag **exige** o argumento seguinte. Se ela for a última da linha, o erro é `Falta valor para <flag>`, inclusive para flags que não existem: `--foo` no fim gera "Falta valor para --foo", e não "Argumento desconhecido".
- `--out` aceita **qualquer** texto como valor, até algo que pareça flag: `--out --elfos` faz `out = "--elfos"`.
- As validações de faixa (`--elfos`, `--renas-ms`, `--timeout-ms`) são feitas **depois** de ler todos os argumentos (`main.c:98-103`).
- `--renas-ms` "obrigatória" é implementada com o padrão −1: se ela não aparece, o valor continua −1 e a validação falha.

### 4.3 Cada flag em detalhe

**`--elfos N`.** Fator A do experimento (3, 6 e 12 na matriz). Define `n_grupos = N/3` e `total_threads = 10 + N` (`main.c:111-112`). Precisa ser múltiplo de 3 porque a versão finita exige que **todo** elfo seja atendido num grupo de exatamente 3: com 7 elfos, um sobraria sem grupo, e o programa nunca terminaria normalmente. O limite de 300 (`MAX_ELFOS`) é de segurança. Exemplo: `--elfos 12` dá 4 grupos e 22 threads.

**`--renas-ms R`.** Fator B (5 = antes, 10 = junto, 30 = depois do primeiro grupo). Todas as 9 renas dormem até `t0 + R` (`rena.c:21`), então chegam praticamente juntas e disputam o mutex. `R = 0` é aceito: as renas chegam logo após a largada. Se `R` for maior que `--timeout-ms`, Noel atende os elfos, fica sem trabalho e o episódio termina em `timeout` (verificado com `--renas-ms 3000`).

**`--rep K` e `--semente S`: parecidas, mas diferentes.**
- `--rep` entra no **nome** da execução (`E06_R10_rep3`). O `graficos.py` usa esse nome para cruzar `resumo.csv` com `espera_elfos.csv`. Repetir o mesmo `--rep` na mesma pasta gera dois conjuntos de linhas com o mesmo nome.
- `--semente` **não influencia nada** na execução: é só uma coluna do `resumo.csv`. O roteiro usa as sementes 11, 22, 33, 44 e 55 como id das repetições. A variação entre repetições vem do escalonador do SO, não de sorteio.

**`--out DIR`.** O programa **não cria** a pasta. A barra final é opcional (`csv.c:47` acrescenta `/` se faltar). Se a pasta não existir, a simulação roda, a linha de resumo é impressa, mas aparece `DIR/resumo.csv: No such file or directory` e o código de saída é **1** [CONFIRMADO 2026-10-28].

**`--timeout-ms MS`.** É uma rede de segurança contra travamento, **não** um limite de duração total:
- o prazo é `t0 + MS`, calculado uma vez (`noel.c:83`);
- ele só é verificado quando Noel **dorme sem trabalho** (`pthread_cond_timedwait`, `noel.c:101`). Se Noel estiver sempre ocupado, a execução pode passar do prazo e terminar `ok`: com `--ajuda-ms 100 --timeout-ms 50`, T = 215 ms e status `ok` [CONFIRMADO 2026-10-28];
- no timeout, quem está no sleep de chegada **não é acordado**. Os joins esperam esses sleeps terminarem: com `--renas-ms 3000` e o padrão de 2000 ms, o status foi `timeout` em T = 2000 ms, mas o processo levou 3,0 s [CONFIRMADO 2026-10-28];
- o valor 2000 ms veio do piloto (maior T = 35,211 ms, ≈ 56× de folga; ver [[Testes e Gráficos (Papai Noel)]]);
- `--timeout-ms 5` serve para **testar o próprio mecanismo**: status `timeout`, 0/6 atendidos, sem travar.

**`--elfo0-ms`, `--ajuda-ms`, `--preparo-ms`.** Durações simuladas por sleep. Nenhuma sincronização depende delas, então qualquer valor, inclusive 0, é aceito. Com `--ajuda-ms 0 --preparo-ms 0`, a execução continua correta (status `ok`), e a utilização de Noel cai para ~0% [CONFIRMADO 2026-10-28]. A matriz oficial usa os padrões 10, 3 e 5. **Atenção:** essas três flags **não aparecem no nome** da execução nem no `resumo.csv`. Se você mudá-las, use outra pasta de saída para não misturar resultados.

**`--teste-prioridade`.** Força o cenário mais difícil: renas e grupo prontos **na mesma decisão**. Noel espera na cond var (sem sleep) até `renas_ok && elfos_ok` (`noel.c:94-98`) e só então passa a decidir normalmente. No fim, a `main` imprime 4 verificações (`main.c:239-254`):

| Verificação | Variável | Passa se |
|---|---|---|
| houve disputa | `decisoes_com_disputa >= 1` | as duas demandas estavam prontas |
| primeira decisão = renas | `primeira_decisao == 1` | a prioridade foi aplicada |
| todos os elfos atendidos | `concluidos == previstos` | nenhum pedido perdido |
| nenhuma violação nem timeout | `violacoes_* == 0 && !abortar` | regras respeitadas |

Saída: código 0 se as 4 passam, 1 se alguma falha. Use `--renas-ms` maior que o fechamento do 1º grupo (≈ 12 ms) para ver a espera; com `--renas-ms 5`, Noel fica "segurando" as renas até 12 ms, e a resposta às renas sobe para ~7 ms (não é violação: é o efeito do modo de teste).

**`--ingenua`.** Troca a regra por `escolhe_renas = !elfos_ok` (`noel.c:117`): elfos primeiro. A própria execução conta a violação (`noel.c:118-119`). Ela só aparece se houver **disputa**:
- `--ingenua` sozinha, com renas em 10 ou 30 ms: 0 violações, porque não houve disputa [CONFIRMADO 2026-10-28];
- `--ingenua --teste-prioridade --renas-ms 30`: 2 violações, status `violacao`, teste FALHOU, código 1 [CONFIRMADO 2026-10-28]. É a demonstração usada no `run_experimentos.sh`.

| Combinação | Para que serve | Nome da execução | `conjunto` |
|---|---|---|---|
| nenhuma | matriz experimental | `E06_R10_rep1` | `referencia`, `1`, `2` ou `fora` |
| `--teste-prioridade` | provar a prioridade | `teste_E06_R30_rep1` | `teste` |
| `--ingenua` | (pouco útil sozinha) | `ingenua_E06_R30_rep1` | `ingenua` |
| as duas | demonstrar a violação | `teste_ingenua_E06_R30_rep1` | `teste_ingenua` |

### 4.4 Argumento omitido ou inválido

Todas as linhas abaixo foram executadas em 2026-10-28 [CONFIRMADO 2026-10-28]. Em todos os casos, a mensagem é seguida do texto de uso.

| Entrada | Mensagem | Código |
|---|---|---|
| (nenhum argumento) | `--elfos deve ser múltiplo de 3 entre 3 e 300` | 64 |
| `--elfos 7`, `--elfos 0`, `--elfos 303` | `--elfos deve ser múltiplo de 3 entre 3 e 300` | 64 |
| `--elfos 6` (sem renas) | `--renas-ms é obrigatório` | 64 |
| `--renas-ms -1` | `Valor inválido para --renas-ms` (`ler_int` rejeita negativos) | 64 |
| `--renas-ms 10abc` | `Valor inválido para --renas-ms` | 64 |
| `--timeout-ms 0` | `--timeout-ms deve ser >= 1` | 64 |
| `--foo 1` | `Argumento desconhecido: --foo` | 64 |
| `--foo` (no fim) | `Falta valor para --foo` | 64 |
| `--out` (no fim) | `Falta valor para --out` | 64 |
| `--help` | só o texto de uso | 64 |
| `--out` para pasta inexistente | `.../resumo.csv: No such file or directory` (a simulação roda) | 1 |

## 5. Códigos de saída

| Código | Quando | Onde |
|---|---|---|
| 0 | execução `ok`, ou `--teste-prioridade` que passou | `main.c:238`, `254` |
| 1 | falta de memória, falha em `pthread_create`, erro ao gravar CSV, ou `--teste-prioridade` que falhou | `main.c:174`, `183`, `189`, `254`, `258-259` |
| 2 | status `timeout` ou `violacao` (fora do modo de teste) | `main.c:255-256` |
| 64 | argumentos inválidos ou `--help` | `main.c:166-169` |

No modo `--teste-prioridade`, um timeout faz o teste falhar e gera código **1**, não 2. Erro de CSV sempre força o código 1.

## 6. Testes

Não há framework de testes unitários nem sanitizers disponíveis. A verificação do projeto é feita por:

| Teste | Comando (em `src/`) | O que comprova | Resultado registrado |
|---|---|---|---|
| Teste funcional de prioridade | `./simulacao --elfos 6 --renas-ms 30 --rep 1 --semente 11 --out ../dados/teste_prioridade/ --teste-prioridade` | com as duas demandas prontas, a 1ª decisão é a viagem | PASSOU (`dados/teste_prioridade/saida.txt`) |
| Demonstração ingênua | o mesmo, com `--ingenua` e `--out ../dados/ingenua/` | a verificação detecta a violação | 2 violações, FALHOU (esperado) |
| Mecanismo de timeout | `./simulacao --elfos 6 --renas-ms 10 --timeout-ms 5 --out <pasta>` | o programa não trava; status `timeout` | `dados/piloto/teste_timeout/` |
| Estresse | parte do `run_experimentos.sh` (300 execuções) | encerramento sem travar nem violar | 300/300 `ok` |
| Invariantes | toda execução | regras contadas em tempo de execução | 0 violações na matriz |

Para rodar o teste funcional **sem** sobrescrever `dados/`, use outra pasta: `mkdir -p /tmp/tp && ./simulacao --elfos 6 --renas-ms 30 --out /tmp/tp/ --teste-prioridade; echo $?` (deve terminar com `RESULTADO: PASSOU` e código 0).

## 7. Experimentos: `run_experimentos.sh`

**Diretório:** qualquer um (o script descobre a raiz pelo próprio caminho, `run_experimentos.sh:17`). Comando: `bash scripts/run_experimentos.sh`. São 343 execuções de 15 a 42 ms cada, mais o tempo de criar cada processo: deve levar bem menos de um minuto [PROVÁVEL 2026-10-28, não cronometrado].

> **O script apaga a rodada anterior.** Ele remove `dados/resumo.csv`, `dados/eventos.csv`, `dados/espera_elfos.csv` e as pastas `dados/piloto`, `teste_prioridade`, `ingenua` e `estresse` (`run_experimentos.sh:29-32`), e reescreve `ambiente.txt` e `compilacao.txt`. **O relatório e os slides citam os números da rodada atual.** Se rodar de novo, os números mudam um pouco (ruído do SO), e você precisa regenerar gráficos, relatório e slides para mantê-los coerentes. Faça uma cópia de `dados/` antes, se quiser preservar a rodada.

| Etapa | Linhas | O que faz | Saída |
|---|---|---|---|
| 1. Ambiente e compilação | 34-59 | registra CPU, SO, gcc, glibc, python; compila; falha se o gcc falhar | `dados/ambiente.txt`, `dados/compilacao.txt` |
| 2. Piloto | 69-84 | 3 execuções × 5 configurações, mais o teste com `--timeout-ms 5`; calcula o maior T | `dados/piloto/` |
| 3. Matriz | 86-95 | **5 configurações × 5 repetições = 25**, intercaladas por repetição, sementes 11..55 | `dados/*.csv` |
| 4. Teste funcional | 97-101 | `--teste-prioridade` | `dados/teste_prioridade/saida.txt` |
| 5. Política ingênua | 103-107 | `--teste-prioridade --ingenua` | `dados/ingenua/saida.txt` |
| 6. Estresse | 109-120 | 100 × {3 elfos/10 ms, 12/5, 12/30} | `dados/estresse/` |

As 5 configurações (`CONFIGS`, linha 25): `6 10` (referência), `3 10` e `12 10` (conjunto 1, varia elfos), `6 5` e `6 30` (conjunto 2, varia renas).

A função `rodar` (linhas 62-67) **não interrompe** o script quando uma execução falha: ela imprime `(código de saída N: ...)` e continua. Procure essas linhas na saída.

## 8. Dos parâmetros aos gráficos: onde cada número nasce

| Grandeza | Definida por | Calculada em | Coluna/arquivo |
|---|---|---|---|
| Quantidade de elfos | `--elfos` | — | `elfos` (`resumo.csv`) |
| Chegada das renas | `--renas-ms` | `rena.c:21` | `renas_ms` |
| Chegada do elfo *i* | `--elfo0-ms` + *i* | `elfo.c:25` | `t_pedido_ms` (`espera_elfos.csv`) |
| Duração da ajuda | `--ajuda-ms` | `noel.c:61` | `inicio_ajuda`/`fim_ajuda` (`eventos.csv`) |
| Duração da preparação | `--preparo-ms` | `noel.c:32` | `inicio_preparacao`/`fim_preparacao` |
| T | — | `noel.c:137` / `metricas.c:43` | `T_ms` |
| Vazão | — | `metricas.c:49`: `concluidos / (T_ms/1000)` | `vazao_pedidos_s` |
| Espera de um elfo | — | `t_inicio_ajuda` (`noel.c:56`) − `t_pedido` (`elfo.c:32`), em `metricas.c:58` | `espera_ms`; média e máximo em `resumo.csv` |
| p95 | — | `metricas.c:17-27`: posição ⌈0,95·n⌉ das esperas ordenadas | `espera_p95_ms` |
| Resposta às renas | — | `t_ini_preparo` (`noel.c:27`) − `t_nona` (`rena.c:31`), em `metricas.c:70` | `resposta_renas_ms` |
| Violação de prioridade | — | `noel.c:118-119` | `violacoes_prioridade` |
| Utilização de Noel | — | `metricas.c:71` | `utilizacao_noel` |

O `graficos.py` usa só os CSVs, sem rodar o programa, e só considera execuções com status `ok`:

| Gráfico | Dados usados (`graficos.py`) | Pergunta que responde |
|---|---|---|
| G1 `G1_vazao_elfos.png` | `resumo.csv`, renas = 10 ms, agrupado por `elfos` (linhas 106-123) | a vazão cresce com o número de elfos? |
| G2 `G2_p95_renas.png` | `resumo.csv`, 6 elfos, agrupado por `renas_ms`: p95 e resposta às renas em µs (125-158) | quanto a chegada das renas pesa na espera dos elfos? |
| G3 `G3_p95_grupo.png` | `espera_elfos.csv` da referência; p95 por execução e grupo (160-184) | o 2º grupo espera mais que o 1º? |
| G4 `G4_linha_tempo.png` | `eventos.csv` da execução `E06_R10_rep1` (186-249) | o que Noel fazia a cada instante? |

O p95 por grupo (G3) e o p95 "agrupado" da tabela usam a função `p95` do Python (`graficos.py:40-45`), com a **mesma** regra ⌈0,95·n⌉ do C. Os números e a forma de apresentar cada gráfico estão em [[Testes e Gráficos (Papai Noel)#Como apresentar cada gráfico]].

## 9. Gráficos, relatório e slides

**Diretório:** qualquer um (os scripts encontram a raiz por `Path(__file__)`).

```bash
.venv/bin/python scripts/graficos.py            # G1–G4 em graficos/ e dados/tabela_esperas.csv
.venv/bin/python scripts/gerar_relatorio.py     # relatorio.pdf (depois do graficos.py)
.venv/bin/python scripts/gerar_slides.py        # slides.pptx (lê CSVs, PNGs e trechos de src/)
```

- `graficos.py` aceita `--dados DIR` (padrão `dados/`) e `--saida DIR` (padrão `graficos/`). **Ele sempre grava `tabela_esperas.csv` dentro da pasta de `--dados`**, mesmo quando `--saida` aponta para outro lugar [CONFIRMADO 2026-10-28, `graficos.py:101`].
- Para gerar os gráficos sem tocar nos PNGs oficiais: `.venv/bin/python scripts/graficos.py --saida /tmp/graf`. A tabela continua sendo regravada em `dados/`, com o mesmo conteúdo enquanto os CSVs não mudarem.
- `gerar_relatorio.py` e `gerar_slides.py` não têm argumentos e sobrescrevem `relatorio.pdf` e `slides.pptx` na raiz. As versões anteriores dos slides estão em `backup/`.

## 10. Limpeza segura

| Artefato | Gerado por | Pode apagar? | Como regenerar |
|---|---|---|---|
| `src/simulacao` | `gcc` | sim | compilar de novo |
| `.venv/` | `python3 -m venv` | sim | seção 1 |
| CSVs de testes manuais em `/tmp/...` | você | sim | — |
| `dados/*.csv`, `dados/piloto/`, `teste_prioridade/`, `ingenua/`, `estresse/`, `ambiente.txt`, `compilacao.txt`, `log_execucao.txt` | `run_experimentos.sh` | **não**, sem necessidade: são os resultados citados no relatório e nos slides | `run_experimentos.sh` (com números um pouco diferentes) |
| `dados/tabela_esperas.csv`, `graficos/*.png` | `graficos.py` | só se for regenerar logo em seguida | `graficos.py` |
| `relatorio.pdf`, `slides.pptx` | scripts Python | não: são entregáveis | scripts da seção 9 |
| `backup/` | manual | não | — |

Limpeza mínima e segura, a partir da raiz do projeto:

```bash
rm -f src/simulacao          # só o binário
rm -rf .venv                 # só se tiver criado o ambiente virtual
```

## 11. Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `dados/resumo.csv: No such file or directory`, código 1 | rodou de dentro de `src/` sem `--out`, ou `--out` aponta para pasta inexistente | `--out ../dados/` ou crie a pasta com `mkdir -p` |
| Usage + código 64 | flag com valor inválido, faltando, ou desconhecida | leia a primeira linha da mensagem (tabela 4.4) |
| `bash: ./simulacao: No such file or directory` | não compilou, ou não está em `src/` | compile (seção 2) |
| `undefined reference to 'pthread_create'` ou a `esperar_largada` | faltou `-pthread`, ou compilou só um `.c` | use o comando completo com `*.c` |
| `ModuleNotFoundError: No module named 'pandas'` | Python do sistema sem as bibliotecas | crie o `.venv` (seção 1) |
| Gráficos com pontos a mais ou médias estranhas | execuções manuais acrescentadas a `dados/*.csv` | rode `run_experimentos.sh` de novo, ou remova as linhas extras |
| Execução com `status=timeout` | `--renas-ms` maior que `--timeout-ms`, ou `--timeout-ms` pequeno demais | aumente `--timeout-ms` (o prazo é contado a partir de `t0`) |
| O processo demora mais que o timeout para terminar | as threads em sleep de chegada não são interrompidas (seção 4.3) | comportamento esperado; não é travamento |
| `-fsanitize=thread`: `cannot find libtsan.so.2` | a biblioteca do TSan não está instalada | instalar o pacote do TSan (`libtsan` no Fedora) [NÃO VERIFICADO] |
| `ModuleNotFoundError` em `gerar_relatorio.py`/`gerar_slides.py` | `reportlab`/`python-pptx` ausentes | `.venv/bin/pip install reportlab python-pptx` |
