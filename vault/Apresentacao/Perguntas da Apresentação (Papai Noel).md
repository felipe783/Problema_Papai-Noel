# Perguntas da Apresentação (Papai Noel)

Cada pergunta tem quatro partes: 🎤 **resposta oral** (30–60 s, para falar), 📘 **aprofundamento** (para você entender), 💻 **no código** (trecho real, de `tema11_papai_noel/src/`) e ❓ **pergunta extra do professor**, com resposta. Base técnica: [[Sincronização no Código (Papai Noel)]], [[Lógica e Fluxo (Papai Noel)]], [[Riscos de Sincronização (Papai Noel)]], [[Testes e Gráficos (Papai Noel)]].

> **Três frases para não errar:** (1) usamos **1 mutex e 4 variáveis de condição, nenhum semáforo**; (2) o mutex é inicializado em **`main.c:131`**, `pthread_mutex_init(&o->mutex, NULL)`, e começa **destravado**; (3) a prioridade é garantida porque **só Noel decide**, com o mutex, testando as renas primeiro, e ele não olha nada enquanto ajuda.

---

## 1. O que é um problema de sincronização?

🎤 **Oral.** "É um problema em que várias threads ou processos compartilham dados ou recursos e a correção depende da **ordem** em que executam. Sem coordenação, duas threads podem mexer na mesma variável ao mesmo tempo e uma apagar o resultado da outra. Também pode acontecer de uma thread precisar esperar um evento produzido por outra. Resolver o problema é garantir duas coisas: exclusão mútua no acesso aos dados e uma forma correta de esperar e avisar, sem desperdiçar CPU e sem travar."

📘 **Aprofundamento.** Há dois tipos de necessidade. A **exclusão mútua** pede que só uma thread por vez execute a seção crítica. A **coordenação ou ordem** pede que uma thread só prossiga quando uma condição for verdadeira ("o grupo foi atendido"). O resultado de um programa concorrente depende do **entrelaçamento** das instruções, que o escalonador escolhe e que muda a cada execução. Um programa só é correto se for correto para **todos** os entrelaçamentos possíveis, e por isso testar não basta.

💻 **No código.** As duas necessidades aparecem na rena: a exclusão mútua (`rena.c:23`, `renas_prontas++` na linha 28) e a espera por evento (`rena.c:36-37`, esperar `viagem_concluida`).

❓ **"Dê um exemplo de entrelaçamento ruim."** Duas renas executam `renas_prontas++` sem lock. As duas leem 7, as duas gravam 8, e o contador fica em 8 com 9 renas presentes. Noel nunca prepara a viagem.

---

## 2. Como problemas de sincronização se relacionam ao Sistema Operacional?

🎤 **Oral.** "O sistema operacional é quem cria e escalona as threads e decide quem roda em cada núcleo e quando uma thread é interrompida. Como não controlamos essa ordem, precisamos de mecanismos para coordenar o acesso. O SO e a biblioteca de threads fornecem esses mecanismos, como o mutex e a variável de condição. Quando uma thread bloqueia num deles, é o SO que a tira da CPU e a acorda depois. Isso evita espera ocupada."

📘 **Aprofundamento.** Preempção, múltiplos núcleos e escalonamento não determinístico são do SO, e são eles que criam as condições de corrida. No Linux, o `pthread_mutex_t` da glibc é implementado em cima da chamada de sistema **futex**: sem disputa, tudo acontece em espaço de usuário; com disputa, a thread pede ao kernel para dormir. Isso é conhecimento sobre a glibc, não foi medido neste trabalho. O próprio kernel resolve os mesmos problemas internamente (filas, buffers, tabelas).

💻 **No código.** `clock_nanosleep` (`tempo.c:48`) e `pthread_cond_timedwait` (`noel.c:101`) são pontos onde a thread **sai da CPU**, e o kernel a acorda no prazo ou no aviso. O relógio `CLOCK_MONOTONIC` (`tempo.c:17`) também é do SO.

❓ **"Threads e processos sincronizam do mesmo jeito?"** Os conceitos são os mesmos. Entre processos, a memória não é compartilhada por padrão, e é preciso memória compartilhada mais mecanismos marcados como compartilháveis (`PTHREAD_PROCESS_SHARED`, ou `sem_init` com 2º argumento ≠ 0) ou mecanismos do kernel (pipes, semáforos nomeados). Aqui são threads de um mesmo processo, e o mutex usa o atributo padrão, privado ao processo.

---

## 3. O que são mutex e semáforo?

🎤 **Oral.** "O mutex é um cadeado com dono: uma thread trava, só ela entra na seção crítica e só ela destrava. Serve para exclusão mútua. O semáforo é um contador com duas operações: `wait`, que decrementa e bloqueia se o valor for zero, e `post`, que incrementa e libera alguém. Serve para contar recursos ou avisar eventos, e qualquer thread pode dar `post`. No nosso trabalho usamos mutex mais variáveis de condição, não semáforos."

📘 **Aprofundamento.** Um semáforo binário (com valor inicial 1) pode imitar um mutex, mas **não tem dono**: outra thread pode liberá-lo. O semáforo **lembra** os avisos no contador; a variável de condição **não lembra** e por isso exige um predicado. A dupla mutex + cond var é mais expressiva para condições compostas ("9 renas **ou** um grupo pronto"), que com semáforos exigiria contadores extras.

💻 **No código.** O mutex é declarado em `comum.h:82` (`pthread_mutex_t mutex;`) e inicializado em `main.c:131`. **Não há nenhum `sem_t`**: um `grep` por `sem_` em `src/` não encontra nada.

❓ **"Então por que não usaram semáforos?"** A espera de Noel depende de um predicado composto, e a prioridade depende de olhar **as duas** demandas ao mesmo tempo. Com mutex + cond var, Noel lê `renas_ok` e `elfos_ok` na mesma seção crítica e decide. Com semáforos (a solução clássica tem `santaSem`), Noel acorda e ainda precisa ler contadores protegidos para saber quem o chamou.

---

## 4. Qual a diferença entre usar só um `if` com contador e usar um mutex?

🎤 **Oral.** "Um `if` que verifica um contador e depois o altera não é atômico. Entre o teste e a alteração, outra thread pode fazer o mesmo teste e as duas passam. É o problema 'verificar e depois agir'. O mutex torna o par 'testar e alterar' indivisível: enquanto uma thread está dentro, a outra espera. No nosso código, o elfo testa se o grupo tem vaga e se inscreve dentro do mutex, e é isso que impede o quarto elfo de invadir."

📘 **Aprofundamento.** `contador++` vira três operações de máquina: ler, somar, gravar. Um `if (n < 3) { membros[n] = id; n++; }` sem proteção permite que dois elfos leiam `n == 2` e ambos escrevam em `membros[2]`. Tentar um "lock caseiro" com flag (`while (ocupado); ocupado = 1;`) também falha, porque o teste e a atribuição da flag sofrem a mesma corrida, além de gastar CPU em espera ocupada. Só uma operação atômica do hardware, usada por dentro do mutex, resolve isso.

💻 **No código.**
```c
// elfo.c:27, 34-41 e 45-51 — tudo com o mutex, sem soltar no meio
pthread_mutex_lock(&o->mutex);
int g = o->grupo_aberto;
Grupo *gr = &o->grupos[g];
if (gr->estado != GRUPO_ABERTO || gr->n >= TAM_GRUPO) { ... }   // o "if" existe,
gr->membros[gr->n++] = id;                                        // mas está DENTRO do mutex
if (gr->n == TAM_GRUPO) { gr->estado = GRUPO_PRONTO; o->grupos_fechados++;
    if (o->grupo_aberto + 1 < o->n_grupos) o->grupo_aberto++; ... }
```

❓ **"Se o `if` está dentro do mutex, ele ainda serve para quê?"** É uma asserção defensiva (`elfo.c:36`). Com o código atual nunca dispara, porque quem fecha o grupo já avança `grupo_aberto`. Se alguém mudasse a lógica e um elfo visse um grupo fechado, ela contaria uma violação em vez de corromper o grupo.

---

## 5. Como o Problema do Papai Noel se relaciona à convivência de threads e processos no SO?

🎤 **Oral.** "Noel é um recurso único e disputado, como uma CPU ou um dispositivo. Elfos e renas são clientes com prioridades diferentes, como processos com prioridade num escalonador. O problema reúne o que o SO faz o tempo todo: exclusão mútua no estado compartilhado, threads dormindo até um evento, agrupar requisições em lotes de três e uma política de prioridade que precisa ser justa. A pergunta 'e se as renas sempre voltassem?' é a mesma pergunta de starvation em escalonadores."

📘 **Aprofundamento.** As analogias são estas. **Lote** (grupo de 3): agrupar requisições de E/S para amortizar custo. **Prioridade sem preempção**: Noel não interrompe uma ajuda, como um escalonador não preemptivo que só decide ao fim do *burst*. **Starvation e aging**: escalonadores por prioridade usam aging para que tarefas de baixa prioridade acabem rodando. **Esperar sem gastar CPU**: threads bloqueadas saem da fila de prontos do SO.

💻 **No código.** A política de escalonamento de Noel é `escolhe_renas = renas_ok` (`noel.c:117`), e o "fim do burst" é o retorno de `ajudar_grupo` (`noel.c:45-74`).

❓ **"Noel seria preemptivo ou não preemptivo?"** **Não preemptivo**: a decisão só acontece entre tarefas (topo do laço em `noel.c:85`), nunca durante uma.

---

## 6. Quais princípios garantem uma boa solução? A nossa atende? Poderia ser melhor?

🎤 **Oral.** "Os critérios clássicos são quatro: exclusão mútua, progresso, espera limitada e não depender da velocidade das threads. Também valem não usar espera ocupada e não ter deadlock. A nossa solução garante exclusão mútua com um único mutex. Garante progresso, porque Noel sempre decide quando há algo pronto. A espera é limitada na versão finita, e o código não depende de tempos, porque os sleeps só simulam a duração das tarefas. Poderia ser melhor em robustez, conferindo os retornos das funções de inicialização, e numa versão contínua precisaria de aging para não deixar os elfos esperando para sempre."

📘 **Aprofundamento.**

| Critério | Atende? | Evidência |
|---|---|---|
| Exclusão mútua | Sim | todo estado mutável só com `mutex` ([[Sincronização no Código (Papai Noel)]], seção 2.4) |
| Progresso | Sim | se `renas_ok` ou `elfos_ok`, Noel decide (`noel.c:100-132`) |
| Espera limitada | Sim (versão finita) | FIFO de grupos + no máximo 1 viagem |
| Sem hipótese de velocidade | Sim | toda espera é por predicado; os sleeps só simulam durações |
| Sem espera ocupada | Sim | todas as esperas são `pthread_cond_wait`/`timedwait` |
| Sem deadlock | Sim | 1 mutex, sem lock aninhado |
| Robustez | **Parcial** | retornos de init não verificados (`main.c:131-139`) |
| Desempenho | Bom para N pequeno | um único mutex serializa tudo; `broadcast` em `cv_elfos` acorda elfos de outros grupos |

**Melhorias possíveis:** conferir os retornos de `pthread_*_init`; usar uma cond var por grupo, ou `signal` direcionado, para evitar acordar elfos de outros grupos; pôr um prazo na espera da largada (`main.c:208`); e, numa versão contínua, aplicar aging ou uma cota para os elfos.

💻 **No código.** Espera sem espera ocupada: `while (gr->estado != GRUPO_CONCLUIDO && !o->abortar) pthread_cond_wait(&o->cv_elfos, &o->mutex);` (`elfo.c:57-58`).

❓ **"Um único mutex não é um gargalo?"** Com 22 threads e seções críticas de microssegundos, não: a resposta às renas fica em ~20 µs. Com milhares de threads seria, e aí valeria separar os locks (um para renas, um para elfos), aceitando o cuidado extra com a ordem de aquisição para não criar deadlock.

---

## 7. O que são starvation e deadlock? Aparecem aqui?

🎤 **Oral.** "Deadlock é quando um grupo de threads fica esperando umas pelas outras para sempre. Normalmente cada uma segura um recurso e quer o da outra. Starvation é quando uma thread nunca consegue progredir porque outras sempre passam na frente. Na nossa implementação não há deadlock: existe um único mutex e ninguém segura um recurso enquanto espera outro. Também não há starvation na versão finita, porque só existe uma viagem e os grupos são atendidos em ordem. Numa versão em que as renas voltassem sempre, a prioridade absoluta poderia deixar os elfos esperando para sempre."

📘 **Aprofundamento.** As condições de Coffman (exclusão mútua, posse e espera, não preempção, espera circular) precisam valer juntas para haver deadlock. Aqui não há **espera circular** entre locks, e quem espera numa cond var **solta** o mutex. Também não existe "deadlock de lógica": todo predicado de espera tem alguém que o torna verdadeiro e avisa. A espera de um grupo na posição *k* é limitada por ≈ 5 + 3(*k* − 1) ms mais o tempo de formação.

💻 **No código.** O timeout de segurança (`noel.c:101-106`) nunca disparou em 25 + 300 execuções. A FIFO é `int g = o->proximo_grupo++;` (`noel.c:128`).

❓ **"O timeout não é admitir que pode haver deadlock?"** Não. É uma **rede de segurança** pedida no enunciado, para gravar `timeout` em vez de travar se algo inesperado acontecer. Limitação: ele não cobre um mutex que nunca é liberado, porque o `timedwait` precisa readquirir o mutex para retornar.

---

## 8. Como apresentar os gráficos e interpretar os resultados?

🎤 **Oral.** "Para cada gráfico dizemos o que ficou fixo, o que variou e quantas execuções há. Depois, a tendência e qual parte da solução a explica. No G1, mais elfos diluem o custo fixo e a vazão vai de 163 para 436 pedidos por segundo. No G2, quando as renas chegam junto, a prioridade atrasa o primeiro grupo e o p95 sobe de 2,1 para 5,2 milissegundos, enquanto as renas são atendidas em cerca de 20 microssegundos. As diferenças são muito maiores que a variação entre repetições, e as 25 execuções foram válidas."

📘 **Aprofundamento.** O roteiro completo e as falas de cada gráfico estão em [[Testes e Gráficos (Papai Noel)]]. Dois cuidados. Primeiro, o p95 de 3 ou 6 amostras é o máximo. Segundo, o resultado do G3 contrariou a intuição (os grupos esperam o mesmo), e dizer isso mostra domínio.

💻 **No código.** A espera é `t_inicio_ajuda − t_pedido`: `t_pedido` é gravado em `elfo.c:32` e `t_inicio_ajuda` em `noel.c:56`. A resposta às renas é `t_ini_preparo` (`noel.c:27`) − `t_nona` (`rena.c:31`).

❓ **"Os resultados provam que a solução está correta?"** Não **provam**. Mostram que as regras valeram em todas as execuções observadas. A correção vem do argumento sobre o código; os testes servem de evidência e o `--ingenua` mostra que o detector de violações funciona.

---

## 9. Como o mutex começa? Qual linha o inicializa?

🎤 **Oral.** "O mutex é um campo da struct compartilhada `Oficina`, declarado em `comum.h`, linha 82. Ele é inicializado na função `iniciar_oficina`, em `main.c`, linha 131, com `pthread_mutex_init(&o->mutex, NULL)`. O primeiro argumento é o endereço do mutex e o segundo, `NULL`, pede os atributos padrão. Ele começa destravado e sem dono. Isso é feito antes de criar qualquer thread, e ele só é destruído depois de todos os joins."

📘 **Aprofundamento.**
- **Ordem:** `main` (`main.c:172`) chama `iniciar_oficina`. A linha 109 faz `memset` da struct, a 131 chama `pthread_mutex_init` e só depois a linha 187 cria a primeira thread.
- **`NULL` = padrão:** tipo `PTHREAD_MUTEX_DEFAULT`, não recursivo, sem verificação de erro, privado ao processo.
- **O `memset` não conta como inicialização** pela POSIX. O que vale é a chamada da linha 131. O código **não** usa `PTHREAD_MUTEX_INITIALIZER`.
- **Retorno não verificado:** `pthread_mutex_init` devolve 0 em sucesso; o código ignora o valor.
- **Fim:** `pthread_mutex_destroy(&o->mutex)` em `main.c:150`, chamada em `main.c:222`.

💻 **No código.**
```c
// main.c:107-110, 131
static int iniciar_oficina(Oficina *o, const Config *c)
{
    memset(o, 0, sizeof *o);
    o->cfg = c;
    ...
    pthread_mutex_init(&o->mutex, NULL);
```

❓ **"O que aconteceria se uma thread usasse o mutex antes da linha 131?"** Comportamento indefinido: o mutex ainda não é um objeto válido. Isso não acontece aqui porque as threads só são criadas em `main.c:187-204`, depois do init.

---

## 10. A implementação usa mutex, semáforo ou ambos?

🎤 **Oral.** "Só mutex, junto com variáveis de condição. Há um mutex e quatro variáveis de condição: `cv_largada` para o sinal de início, `cv_noel` onde Noel dorme, `cv_elfos` onde os elfos esperam a ajuda acabar e `cv_renas` onde as renas esperam a viagem. Não usamos nenhum semáforo nem barreira da biblioteca. O sinal de início é uma barreira construída com contador, mutex e variável de condição."

📘 **Aprofundamento.** A tabela completa, com linha de declaração e de inicialização de cada mecanismo, está em [[Sincronização no Código (Papai Noel)]], seção 1. O papel que os semáforos têm na solução clássica de Downey (`santaSem`, `reindeerSem`, `elfTex`) é cumprido por predicados com cond vars e pela fila de grupos com id (seção 3 da mesma nota).

💻 **No código.** `comum.h:82-86` declara `mutex`, `cv_largada`, `cv_noel`, `cv_elfos` e `cv_renas`; `main.c:131-140` os inicializa.

❓ **"Variável de condição sozinha resolve?"** Não. Ela sempre trabalha com um mutex: `pthread_cond_wait(&cv, &mutex)` exige o mutex travado, e o predicado testado no `while` é um dado protegido por esse mutex.

---

## 11. Qual valor inicial cada mecanismo recebe e por quê?

🎤 **Oral.** "O mutex começa destravado, para que a primeira thread possa entrar. As variáveis de condição não têm valor: começam sem ninguém esperando. O que tem valor inicial são as variáveis que elas observam, e todas começam em zero pelo `memset`: nenhuma rena pronta, nenhum grupo fechado, viagem não concluída, largada não dada, sem abortar. A `cv_noel` também recebe um atributo especial, o relógio monotônico, para o timeout ser medido no mesmo relógio que o `t0`."

📘 **Aprofundamento.**

| Mecanismo ou variável | Valor inicial | Onde | Por quê |
|---|---|---|---|
| `mutex` | destravado | `main.c:131` | ninguém dentro no começo |
| `cv_largada`, `cv_elfos`, `cv_renas` | fila vazia, atributos padrão | `main.c:132-134` | cond var não tem valor |
| `cv_noel` | fila vazia, relógio `CLOCK_MONOTONIC` | `main.c:136-140` | o prazo `t0 + timeout` (`noel.c:83`) é monotônico |
| `largada`, `threads_prontas` | 0 | `memset`, `main.c:109` | ninguém pode começar antes da main |
| `total_threads` | 1 + 9 + N | `main.c:112` | quantas a largada espera |
| `renas_prontas`, `viagem_*` | 0 | `memset` | nenhuma rena, nenhuma viagem |
| `grupos[k].n`, `.estado` | 0, `GRUPO_ABERTO` | `calloc`, `main.c:116` | todos os grupos vazios e abertos |
| `grupo_aberto`, `grupos_fechados`, `proximo_grupo` | 0, 0, 0 | `memset` | o primeiro grupo recebe elfos; a fila começa vazia |
| `estado` de Noel | `NOEL_DORMINDO` | `main.c:113` | sem tarefa |

💻 **No código.** `pthread_condattr_setclock(&at, CLOCK_MONOTONIC);` (`main.c:138`).

❓ **"Por que não `CLOCK_REALTIME`, que é o padrão?"** Porque `t0` e o prazo vêm de `CLOCK_MONOTONIC` (`tempo.c:17`). Misturar relógios faria o timeout disparar na hora ou nunca, e o relógio de tempo real pode ser ajustado pelo sistema durante a execução.

---

## 12. Qual a diferença entre inicializar um mutex e inicializar um semáforo?

🎤 **Oral.** "O mutex é inicializado sem valor numérico: `pthread_mutex_init` recebe só o endereço e os atributos, e ele sempre começa destravado. O semáforo é inicializado com um número, `sem_init(&s, 0, valor)`, e esse valor muda o comportamento: 1 funciona como uma tranca, 0 faz a primeira espera bloquear até alguém avisar, e N permite N threads ao mesmo tempo. No nosso código só existe a primeira inicialização, a do mutex."

📘 **Aprofundamento.** `sem_init(sem_t *s, int pshared, unsigned valor)`: `pshared = 0` compartilha entre threads do processo e ≠ 0 entre processos (com memória compartilhada); `valor` é o contador inicial. No mutex, o "estado inicial" é fixo (livre), e os atributos definem **tipo** (normal, recursivo, com verificação de erro), **compartilhamento** e **protocolo de prioridade**. Também há inicialização estática: `PTHREAD_MUTEX_INITIALIZER` para mutex, que não é usada aqui.

💻 **No código.** `pthread_mutex_init(&o->mutex, NULL);` (`main.c:131`). Não há `sem_init` no projeto.

❓ **"Um semáforo inicializado com 1 é igual a um mutex?"** Funciona como exclusão mútua, mas **não tem dono**: qualquer thread pode dar `post`, até uma que não deu `wait`. O mutex só pode ser destravado por quem travou, o que pega mais erros e permite, por exemplo, herança de prioridade.

---

## 13. O que aconteceria se o valor inicial de um semáforo fosse diferente?

🎤 **Oral.** "Não usamos semáforos, então respondo pensando na solução clássica. Se o semáforo em que Noel dorme começasse em 1 em vez de 0, Noel acordaria logo no início sem nenhuma demanda. Se o semáforo que serve de tranca começasse em 0, ninguém conseguiria entrar e o programa travaria. Se começasse em 2, duas threads entrariam na seção crítica ao mesmo tempo. No nosso código o equivalente seria iniciar as variáveis de estado com valores errados, por exemplo `renas_prontas` em 1: a viagem sairia com só 8 renas."

📘 **Aprofundamento.** O valor inicial de um semáforo é **um aviso ou recurso que já existe**. Na solução de Downey: `mutex = 1` (com 0, deadlock imediato; com 2, perde a exclusão); `santaSem = 0` (com 1, Noel acorda sem motivo, e no código clássico iria checar contadores e poderia agir errado); `reindeerSem = 0` (com valor > 0, renas sairiam antes da preparação); `elfTex = 1` (com 0, nenhum elfo entra; com 2, dois grupos se formariam em paralelo). No nosso código, a "memória" fica nas variáveis zeradas pelo `memset`. É por isso que o `memset` em `main.c:109` e o `calloc` em `main.c:116` são importantes.

💻 **No código.** O equivalente do "valor inicial" é o predicado: `renas_ok = o->renas_prontas == NUM_RENAS && !o->viagem_iniciada;` (`noel.c:89`). Com `renas_prontas` começando em 1, a 8ª rena já faria a condição valer.

❓ **"E na variável de condição, um valor inicial errado faria diferença?"** A cond var não tem valor. O que pode estar errado é o **predicado**, por exemplo `largada = 1` desde o início: as threads começariam antes de `t0` ser gravado, e os tempos medidos ficariam errados.

---

## 14. Por que uma thread bloqueia e o que a faz voltar?

🎤 **Oral.** "Ela bloqueia em dois casos. No primeiro, tenta travar um mutex que outra thread segura e espera até ele ser liberado. No segundo, testa uma condição, a condição é falsa e ela chama `pthread_cond_wait`: solta o mutex e dorme. Ela volta quando outra thread muda o estado e dá `signal` ou `broadcast`, ou no timeout de Noel. Ao acordar, ela retrava o mutex e testa a condição de novo, porque pode ter acordado sem motivo ou outra thread pode ter mudado o estado antes."

📘 **Aprofundamento.**

| Quem | Onde bloqueia | Condição para continuar | Quem libera |
|---|---|---|---|
| Qualquer thread | `pthread_mutex_lock` | o mutex ficar livre | o `unlock` da dona |
| Threads | `main.c:30` (`cv_largada`) | `largada == 1` | main, `main.c:212` |
| Main | `main.c:209` | `threads_prontas == total_threads` | cada thread, `main.c:28` |
| Noel | `noel.c:101` (`cv_noel`) | `renas_ok \|\| elfos_ok` ou prazo vencido | 9ª rena `rena.c:33`; 3º elfo `elfo.c:53`; o kernel no timeout |
| Elfo | `elfo.c:58` (`cv_elfos`) | seu grupo `CONCLUIDO` ou `abortar` | Noel, `noel.c:73` e `143` |
| Rena | `rena.c:37` (`cv_renas`) | `viagem_concluida` ou `abortar` | Noel, `noel.c:41` e `144` |
| Todas | `clock_nanosleep` (`tempo.c:48`) | chegar o instante simulado | o kernel; **não** é sincronização |

💻 **No código.**
```c
// rena.c:36-38
while (!o->viagem_concluida && !o->abortar)
    pthread_cond_wait(&o->cv_renas, &o->mutex);
pthread_mutex_unlock(&o->mutex);
```

❓ **"E se o `signal` acontecer antes de a thread começar a esperar?"** Ele se perde, mas isso não é problema: o **estado** já mudou, e a thread testa o predicado antes de dormir. Exemplo real: o grupo 2 ficou pronto (15,061 ms) com Noel preparando a viagem, fora de `cv_noel`. Ao voltar ao laço, Noel viu a fila e atendeu os grupos sem precisar do aviso.

---

## 15. Como a implementação garante prioridade às renas sem interromper a ajuda?

🎤 **Oral.** "Por duas razões. Primeiro, só a thread do Noel decide. Ela trava o mutex, lê ao mesmo tempo se as nove renas estão prontas e se há grupo na fila, e testa as renas primeiro. Como a leitura e a decisão acontecem na mesma seção crítica, ninguém muda o estado no meio. Segundo, durante a ajuda Noel só dorme três milissegundos e não olha nada. Se a nona rena chega nesse meio tempo, ela atualiza o contador e avisa, mas Noel só vai reavaliar quando terminar. No teste de prioridade, com renas e dois grupos prontos ao mesmo tempo, a primeira decisão foi a viagem. Na versão ingênua, o programa detectou duas violações."

📘 **Aprofundamento.** A prioridade é avaliada **nos pontos de decisão** (o topo do laço), não continuamente: é uma política **não preemptiva**. A janela entre "Noel decide pelo grupo" e "a 9ª rena chega" não é violação, porque, para o programa, a rena ainda não estava pronta no estado lido. O detector (`noel.c:118-119`) conta uma violação quando Noel escolhe elfos com `renas_ok == 1`. Ele deu 0 na matriz e 2 no `--ingenua`, o que mostra que o detector funciona.

💻 **No código.**
```c
// noel.c:89-90, 117, 123-132 — com o mutex adquirido
int renas_ok = o->renas_prontas == NUM_RENAS && !o->viagem_iniciada;
int elfos_ok = o->proximo_grupo < o->grupos_fechados;
...
int escolhe_renas = c->ingenua ? !elfos_ok : renas_ok;
if (escolhe_renas) { ...; preparar_viagem(o); }
else { int g = o->proximo_grupo++; ...; ajudar_grupo(o, g); }

// noel.c:60-62 — durante a ajuda: sem mutex, sem decisão
pthread_mutex_unlock(&o->mutex);
dormir_ate_ms(o, inicio + o->cfg->ajuda_ms);
pthread_mutex_lock(&o->mutex);
```

❓ **"Se Noel solta o mutex durante a ajuda, outra thread não pode 'roubar' o grupo ou começar outra ajuda?"** Não. Só a thread Noel executa `ajudar_grupo`/`preparar_viagem`. Elfos e renas apenas se inscrevem e avisam. O grupo em ajuda está marcado como `EM_AJUDA` (`noel.c:51`) e saiu da fila (`proximo_grupo` já avançou, `noel.c:128`), então ninguém mais o toca até Noel marcá-lo `CONCLUIDO`.
