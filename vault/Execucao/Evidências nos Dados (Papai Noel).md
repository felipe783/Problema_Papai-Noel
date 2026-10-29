# Evidências nos Dados (Papai Noel)

O que é **cada conjunto de dados** do trabalho, o que ele mostra e **qual conclusão ele sustenta**, com as tabelas prontas para mostrar na apresentação. Os campos de cada CSV, um a um, estão em [[Saída do Programa (Papai Noel)]]. Os gráficos estão em [[Interpretação dos Gráficos (Papai Noel)]], e os números da matriz em [[Testes e Gráficos (Papai Noel)]]. Índice: [[_Papai-Noel]].

> **Duas origens, sempre diga qual.** **Dados do projeto:** tudo o que está em `tema11_papai_noel/dados/`, gerado por `scripts/run_experimentos.sh` em 2026-10-28. **Verificações avulsas:** execuções feitas fora do projeto em 2026-10-28, com o mesmo binário compilado de `src/`, que **não estão salvas** em `dados/`. Cada tabela abaixo diz de qual das duas vem.

## Sumário

1. Mapa dos dados: o que é cada arquivo
2. Evidência 1: o mutex põe as 9 renas em fila
3. Evidência 2: o Noel só segura o mutex por instantes
4. Evidência 3: esperar não gasta CPU
5. Evidência 4: a matriz oficial
6. Evidência 5: correta × ingênua
7. Evidência 6: testes de sensibilidade
8. Evidência 7: robustez (piloto, timeout, estresse)
9. Conclusões: observado, garantido e limites
10. Qual tabela mostrar para cada pergunta

---

## 1. Mapa dos dados: o que é cada arquivo

### 1.1 Dados do projeto (`tema11_papai_noel/dados/`)

| Arquivo ou pasta | O que é | Quantidade | Comando que gerou | Para que serve |
|---|---|---|---|---|
| `resumo.csv` | **uma linha por execução** da matriz oficial: T, vazão, esperas, resposta às renas, violações, utilização, status | 25 linhas (5 configurações × 5) | `run_experimentos.sh` | G1, G2 e a tabela de resultados |
| `eventos.csv` | **a linha do tempo**: cada chegada, decisão, início e fim de tarefa, com instante (ms) e estado do Noel | 735 eventos | idem | G4, slides 14 e 17, evidências 1 e 2 |
| `espera_elfos.csv` | **uma linha por elfo**: instante do pedido, início da ajuda e espera | 165 elfos | idem | G3, espera por grupo |
| `tabela_esperas.csv` | **resumo por configuração** (médias, mín–máx, taxa de válidas), calculado por `graficos.py` | 5 linhas | `scripts/graficos.py` | números citados nos slides |
| `log_execucao.txt` | a saída de console de cada execução, incluindo `decisoes` e `com disputa` | — | `run_experimentos.sh` | prova de que a matriz **não teve disputa** |
| `ambiente.txt` | máquina, CPU (12 lógicas), SO, kernel, GCC, glibc, Python | — | idem | reprodutibilidade |
| `compilacao.txt` | saída do GCC | vazio = **0 warnings** | idem | compila limpo com `-Wall -Wextra` |
| `teste_prioridade/` | o mesmo cenário com o Noel "segurado" até haver disputa | 1 execução | `--elfos 6 --renas-ms 30 --teste-prioridade` | testa a **regra de prioridade** |
| `ingenua/` | o mesmo cenário com a regra invertida (elfos primeiro) | 1 execução | idem + `--ingenua` | prova que o **detector de violações funciona** |
| `piloto/` | rodada inicial, antes da matriz | 15 execuções (5 configurações × 3) | `run_experimentos.sh` | escolher o timeout (maior T = 35,2 ms) |
| `piloto/teste_timeout/` | o timeout disparado de propósito | 1 execução | `--timeout-ms 5` | prova que o timeout **encerra sem travar** |
| `estresse/` | repetição em massa | 300 execuções (3 configurações × 100) | `run_experimentos.sh` | procurar falhas raras |

### 1.2 Verificações avulsas (fora de `dados/`, 2026-10-28)

| Verificação | Comando | Usada em |
|---|---|---|
| Muitos elfos | `--elfos 24` e `--elfos 48`, renas em 10 ms | evidência 6, G1 |
| Ajuda mais lenta ou mais rápida | `--elfos 12 --ajuda-ms 4` e `--elfos 6 --ajuda-ms 2` | evidência 6, G3 |
| Rena chega durante a ajuda | `--elfos 6 --renas-ms 13` | evidência 6, slide 16 |
| Empate rena × elfo | 30 × `--elfos 6 --renas-ms 12` | evidência 6, slide 31 |
| Uso de CPU | `/usr/bin/time` com `--elfos 6` (3×) e `--elfos 48` | evidência 3 |

> Os slides 16 e 31 usam números de execuções avulsas **anteriores**, digitados em `gerar_apresentacao.py`. Os valores exatos variam alguns µs a cada execução; a ordem dos eventos e a ausência de violações se repetem.

---

## 2. Evidência 1: o mutex põe as 9 renas em fila

**Origem:** dados do projeto, `eventos.csv`, execução `E06_R10_rep1`.

As 9 renas dormem até o **mesmo** instante (10 ms, `rena.c:21`) e todas chamam `pthread_mutex_lock` em `rena.c:23`. Cada uma registra a chegada **depois** de conseguir o mutex:

| Ordem | Rena | Registrou em (ms) | `renas_prontas` depois |
|---|---|---|---|
| 1 | 9 | 10,061 | 1 |
| 2 | 5 | 10,062 | 2 |
| 3 | 7 | 10,063 | 3 |
| 4 | 2 | 10,069 | 4 |
| 5 | 6 | 10,070 | 5 |
| 6 | 8 | 10,072 | 6 |
| 7 | 4 | 10,078 | 7 |
| 8 | 1 | 10,079 | 8 |
| 9 | **3** | **10,091** | **9** → grava `t_nona` e acorda o Noel |

**O que mostra:**
- **Exclusão mútua:** acordaram juntas, mas passaram pela seção crítica **uma de cada vez**, em 30 µs. Cada `renas_prontas++` foi feito sozinho, por isso o contador chegou exatamente a 9.
- **A ordem é do escalonador:** 9, 5, 7, 2, 6, 8, 4, 1, 3, não a ordem dos ids. A POSIX não garante FIFO no mutex.
- **"A 9ª rena" não é uma rena fixa:** é quem pegou o mutex por último. Aqui foi a rena 3; no teste de prioridade, a rena 2.

**Conclusão:** o mutex serializa o acesso ao contador. Sem ele, duas renas poderiam ler o mesmo valor e um incremento se perderia (slide 4, hipotético).

---

## 3. Evidência 2: o Noel só segura o mutex por instantes

**Origem:** dados do projeto (`eventos.csv`, `E06_R10_rep1`), cruzados com o código de `noel.c`. Quem tem o mutex em cada trecho é **dedução pelo código**; o tempo exato com o mutex não foi medido.

| Tempo (ms) | O que acontece | Quem tem o mutex | Código |
|---|---|---|---|
| 0 → 10,09 | o Noel dorme em `cv_noel`: não há nada pronto | ninguém / quem se registrar | `noel.c:101` |
| 10,061 → 10,091 | as 9 renas se registram, uma de cada vez | cada rena, por µs | `rena.c:23-37` |
| 10,108 | o Noel acorda, testa, decide **viagem** e anota o início | **Noel**, por µs | `noel.c:89-128`, `24-28` |
| 10,108 → 15,185 | o Noel prepara a viagem: `unlock`, dorme 5 ms, `lock` | **livre** para os elfos | `noel.c:31-33` |
| 11,07 / 12,07 / 13,07 / 14,06 / 15,06 | os elfos chegam, se inscrevem e fecham grupos **durante** a viagem | cada elfo, por µs | `elfo.c:27-59` |
| 15,185 | o Noel marca a viagem concluída e solta as 9 renas | **Noel**, por µs | `noel.c:35-41` |
| 15,200 | o Noel decide o **grupo 1** (já havia 2 grupos na fila) | **Noel**, por µs | `noel.c:85-131` |
| 15,200 → 18,271 | ajuda o grupo 1: `unlock`, dorme 3 ms, `lock` | livre | `noel.c:60-62` |
| 18,279 → 21,358 | o mesmo para o grupo 2 | livre | idem |
| 21,362 | encerramento: o Noel solta o mutex e termina | Noel, por µs | `noel.c:135-145` |

**O que mostra:**
- O Noel **não fica com o mutex** e **não fica monitorando**. Ele dorme em `cv_noel` (o `cond_wait` solta o mutex ao dormir e o retoma ao acordar), e quem completa uma demanda (a 9ª rena, o 3º elfo) é quem o acorda.
- Os elfos conseguem se inscrever **durante** a viagem justamente porque o Noel soltou o mutex. É o que se vê no G4: os traços de chegada ficam dentro da faixa laranja.
- **Do sinal à decisão: 17 µs** (10,091 → 10,108). Isso não é um atraso programado, é o custo do SO para acordar o Noel e devolver o mutex.

---

## 4. Evidência 3: esperar não gasta CPU

**Origem:** verificação avulsa, `/usr/bin/time ./simulacao ...`, 2026-10-28.

| Execução | Tempo de relógio | CPU (todas as threads, % de 1 núcleo) | Trocas de contexto voluntárias | Involuntárias |
|---|---|---|---|---|
| 6 elfos, renas 10 ms (1ª) | 0,02 s | 17% | 196 | 3 |
| 6 elfos, renas 10 ms (2ª) | 0,02 s | 8% | 216 | 4 |
| 6 elfos, renas 10 ms (3ª) | 0,02 s | 13% | 182 | 6 |
| 48 elfos, renas 10 ms | 0,06 s | 18% | 1515 | 35 |

**Como ler:**
- **CPU:** 16 threads vivas por ~20 ms usam uma **fração de um núcleo**, incluindo criar as threads e gravar os CSVs. A máquina tem 12 núcleos lógicos.
- **Trocas voluntárias:** quantas vezes uma thread **desistiu da CPU por conta própria** porque ia esperar (sleep, `cond_wait`, fila do mutex). É a maioria.
- **Trocas involuntárias:** quantas vezes o SO **tirou** uma thread que queria continuar (preempção). Quase nunca, porque ninguém fica rodando tempo suficiente.
- **Limite da medida:** o `time` tem resolução de 10 ms, por isso `user` e `sys` saem 0,00. A porcentagem e as trocas de contexto são os números úteis.

**Conclusão:** thread bloqueada no mutex, numa variável de condição ou num sleep **sai da fila de execução** e não usa CPU. Com espera ocupada (`while (!pronto) {}`), as 16 threads girariam o tempo todo. Isso é hipotético, não foi executado.

> **Armadilha:** "utilização do Noel" (52,5% na referência) **não é uso de CPU**. É o tempo em que ele está ajudando ou preparando, dividido por T, e essas tarefas são sleeps. O Noel está "ocupado" no sentido do problema, não do processador.

---

## 5. Evidência 4: a matriz oficial

**Origem:** dados do projeto, `resumo.csv` e `tabela_esperas.csv`. Médias de 5 repetições; mín–máx entre parênteses.

| Config. | Elfos | Renas | Vazão (pedidos/s) | p95 da espera (ms) | Resposta às renas (µs) | Util. Noel | Válidas |
|---|---|---|---|---|---|---|---|
| E03_R10 | 3 | junto | 163,4 (160,0–164,3) | 5,21 (5,11–5,56) | 24 | 44,8% | 5/5 |
| **E06_R10** | **6** | **junto** | **280,9 (280,2–281,3)** | **5,20 (5,17–5,25)** | **18** | **52,5%** | **5/5** |
| E12_R10 | 12 | junto | 436,2 (435,4–437,0) | 5,37 (5,32–5,41) | 20 | 63,1% | 5/5 |
| E06_R05 | 6 | antes | 328,7 (328,5–328,9) | 2,10 (2,10–2,11) | 20 | 61,5% | 5/5 |
| E06_R30 | 6 | depois | 170,0 (168,9–170,6) | 2,11 (2,10–2,12) | 21 | 32,0% | 5/5 |

**Totais:** 25/25 execuções `ok`, 0 violações de prioridade, 0 violações de regras, **0 decisões com disputa** (`log_execucao.txt`).

| O que os dados mostram | Conclusão |
|---|---|
| Vazão sobe com os elfos, ~2% abaixo da conta T ≈ 15 + N ms | o custo fixo inicial se dilui; o Noel atende um grupo atrás do outro (G1) |
| p95 de 5,2 ms só com renas "junto" | o grupo 1 fecha durante a viagem e espera: é o **custo da prioridade** (G2) |
| p95 de 2,1 ms com renas antes ou depois | é o 1º elfo esperando os colegas formarem o grupo, não espera pelo Noel |
| Resposta às renas de 18–24 µs em todas | o Noel acorda pela variável de condição em µs quando está livre |
| Variação entre repetições < 3% | o cenário é dirigido pelo relógio; o ruído é o escalonador do SO |
| 0 decisões com disputa | a matriz **não exercita** a regra de prioridade; isso é feito pela evidência 5 |

---

## 6. Evidência 5: correta × ingênua

**Origem:** dados do projeto, `dados/teste_prioridade/` e `dados/ingenua/`. Mesmo cenário: 6 elfos, renas em 30 ms, o Noel segurado até haver disputa.

| | Correta | Ingênua |
|---|---|---|
| Regra (`noel.c:117`) | `escolhe_renas = renas_ok` | `escolhe_renas = !elfos_ok` |
| Grupos prontos | 12,06 e 15,06 ms | 12,08 e 15,07 ms |
| 9ª rena | 30,455 ms | 30,106 ms |
| 1ª decisão | **viagem** (30,473) | **grupo 1** (30,113) |
| Ordem | viagem → g1 → g2 | g1 → g2 → viagem |
| Resposta às renas | **18 µs** | **6,145 ms** |
| Decisões com disputa | **1** (`log_execucao.txt`, linha `teste_E06_R30_rep1`) | — |
| Violações de prioridade | **0** | **2** |
| T | 41,93 ms | 41,33 ms |
| Maior espera dos elfos | 25,8 ms | 20,1 ms |
| Resultado | PASSOU (código de saída 0) | violação |

**Conclusões:**
- Os mecanismos (mutex e variáveis de condição) são **idênticos**: só a regra de decisão muda o resultado. A prioridade vem da **política**, não do lock.
- O detector de violações **funciona**: contou 2.
- **Desempenho não mede correção:** a ingênua terminou **antes** e os elfos esperaram **menos**, e mesmo assim ela está errada.
- As esperas de 20–26 ms são artificiais (o Noel foi segurado até 30 ms). Não compare com a matriz.

---

## 7. Evidência 6: testes de sensibilidade

**Origem:** verificações avulsas, 2026-10-28, uma execução cada (exceto o empate).

### 7.1 Mais elfos (o que o G1 faria além de 12)

| Elfos | Previsto N/(15+N)·1000 | Medido (pedidos/s) | p95 (ms) | Util. Noel |
|---|---|---|---|---|
| 3 (matriz) | 166,7 | 163,4 | 5,21 | 44,8% |
| 6 (matriz) | 285,7 | 280,9 | 5,20 | 52,5% |
| 12 (matriz) | 444,4 | 436,2 | 5,37 | 63,1% |
| 24 | 615 | 601,2 | 5,68 | 74,3% |
| 48 | 762 | 744,2 | 6,18 | 84,0% |

**Conclusão:** a vazão continua subindo, cada vez menos, rumo a **1000/s**, a capacidade do Noel (3 elfos a cada 3 ms). Mais threads não trazem paralelismo: o Noel atende um grupo por vez.

### 7.2 Duração da ajuda (por que o G3 sai plano)

Maior espera de cada grupo (ms), renas em 10 ms:

| Grupo | Ajuda 2 ms (6 elfos) | Ajuda 3 ms (padrão, ref.) | Ajuda 4 ms (12 elfos) |
|---|---|---|---|
| 1 | 5,14 | 5,12 | 5,10 |
| 2 | **4,22** | 5,20 | **6,25** |
| 3 | — | — | **7,34** |
| 4 | — | — | **8,43** |

**Conclusão:** os grupos ficam prontos a cada 3 ms.
- **Ajuda < 3 ms:** a fila **esvazia** e a espera cai.
- **Ajuda = 3 ms:** a espera fica **estável**.
- **Ajuda > 3 ms:** a fila **cresce** ~1,1 ms por grupo.

É a regra de qualquer fila (inclusive de um escalonador de SO): se chega trabalho mais rápido do que se atende, a espera cresce.

### 7.3 A rena chega durante uma ajuda (`--renas-ms 13`)

| Evento | Tempo (ms) |
|---|---|
| Grupo 1 pronto → decisão: ajudar o grupo 1 | 12,102 → 12,136 |
| **9ª rena chega** (o Noel está ajudando) | **13,087** |
| Grupo 2 pronto | 15,069 |
| Fim da ajuda ao grupo 1 | 15,213 |
| **Decisão com disputa: viagem vence** | **15,221** |
| Fim da preparação → ajuda ao grupo 2 | 20,298 → 20,313 |

Resposta às renas = **2,134 ms** (contra ~20 µs com o Noel livre). Status `ok`, 0 violações, `com disputa: 1`.

**Conclusão:** a prioridade é **não preemptiva**. A ajuda iniciada não é interrompida, e a prioridade vale no **próximo** ponto de decisão.

### 7.4 Empate rena × 3º elfo (`--renas-ms 12`, 30 execuções)

| Rodada | 1ª decisão = viagem | 1ª decisão = grupo 1 | Violações |
|---|---|---|---|
| slide 31 | 12 | 18 | 0 |
| outra nota do vault | 8 | 22 | 0 |
| reexecução de 2026-10-28 | 10 | 20 | 0 |

**Conclusão:** quem pega o mutex primeiro é decidido pelo escalonador, por isso a proporção muda. O que **não muda** é 0 violações: se o grupo é registrado antes da rena, para o programa a rena ainda não chegou.

---

## 8. Evidência 7: robustez (piloto, timeout, estresse)

**Origem:** dados do projeto.

| Teste | O que foi feito | Resultado | Conclusão |
|---|---|---|---|
| Piloto | 15 execuções (5 configurações × 3) | maior T = 35,211 ms | timeout de 2000 ms ≈ 56× o maior T: não dispara por acaso |
| Timeout forçado | `--timeout-ms 5` | status `timeout`, 0/6 atendidos, código de saída 2, sem travar | o mecanismo de segurança encerra e acorda todo mundo |
| Estresse | 100 × E03_R10, 100 × E12_R05, 100 × E12_R30 | **300/300 `ok`**, maior T = 35,688 ms | nenhuma falha rara apareceu em 300 tentativas |
| Compilação | `gcc -std=c11 -O2 -Wall -Wextra -pthread` | 0 warnings | sem avisos do compilador |

---

## 9. Conclusões: observado, garantido e limites

| Observado nos dados | Garantido pelo código | Limites da evidência |
|---|---|---|
| 25/25 execuções `ok`, 0 violações | grupo de 3 sem invasão: inscrever e fechar na mesma seção crítica (`elfo.c:41-53`) | na matriz, **0 decisões com disputa**: a prioridade só foi testada pelos testes dedicados |
| teste de prioridade PASSOU; ingênua com 2 violações | viagem só com 9 renas, uma vez (`noel.c:89`) | algumas checagens nunca disparam por construção: "0" nelas não prova nada sozinho |
| 300/300 no estresse | renas primeiro sobre o estado lido com o mutex (`noel.c:117`) | ThreadSanitizer e Helgrind não foram executados |
| renas serializadas pelo mutex (evidência 1) | tarefa iniciada não é interrompida (`noel.c:31-33`, `60-62`) | quem "chega primeiro" num empate depende do escalonador |
| esperas sem gastar CPU (evidência 3) | toda espera é `while` + predicado: aviso perdido não trava ninguém | slides 16 e 31 vêm de execuções avulsas, sem CSV salvo |

**Frase-síntese:** os dados mostram que **as regras valeram em todas as execuções observadas**. A **garantia** vem da análise do código. Testes mostram a presença de erros, não a ausência.

---

## 10. Qual tabela mostrar para cada pergunta

| Se o professor perguntar… | Mostre |
|---|---|
| "Como você sabe que o mutex funciona?" | Evidência 1 (renas em fila) |
| "O Noel fica com o lock o tempo todo?" | Evidência 2 (quem tem o mutex em cada trecho) |
| "Threads esperando gastam CPU?" | Evidência 3 |
| "Quais foram os resultados?" | Evidência 4 (matriz) |
| "Como garantem a prioridade?" | Evidência 5 (correta × ingênua) |
| "E com mais threads?" | Evidência 6.1 |
| "Por que o 2º grupo não espera mais?" | Evidência 6.2 |
| "E se a rena chegar durante a ajuda?" | Evidência 6.3 |
| "E se chegarem juntos?" | Evidência 6.4 |
| "O programa pode travar?" | Evidência 7 (timeout e estresse) |
| "Isso prova que está correto?" | Seção 9 |
