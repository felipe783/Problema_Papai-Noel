# Laços do Código (Papai Noel)

A **lógica** dos laços do programa, sem entrar em linhas de código: quem repete o quê, o que faz cada laço girar de novo e o que o faz parar. Para o passo a passo com `arquivo:linha`, veja [[Fluxo do Código e Sincronização (Papai Noel)]]. Para os mecanismos (mutex e cond vars), veja [[Sincronização no Código (Papai Noel)]].

Índice: [[_Papai-Noel]].

> Lido no código de `tema11_papai_noel/src/` em 2026-10-28 [CONFIRMADO 2026-10-28].

## Visão geral

Só existe **um laço de verdade que decide coisas**: o do Noel. Os outros laços são esperas: cada thread fica parada até a condição dela virar verdadeira.

```mermaid
flowchart TD
    A["main: lê argumentos e prepara a oficina"] --> B["Cria Noel, 9 renas e N elfos"]
    B --> C{"Todas as threads<br/>já estão esperando?"}
    C -- não --> C1["main espera"] --> C
    C -- sim --> D["Largada: marca t0 e acorda todas"]
    D --> N["Laço do Noel"]
    D --> R["Cada rena: chega e espera a viagem"]
    D --> E["Cada elfo: chega, entra num grupo e espera a ajuda"]
    R -. "9ª rena acorda Noel" .-> N
    E -. "3º elfo do grupo acorda Noel" .-> N
    N -. "viagem pronta: libera as renas" .-> R
    N -. "ajuda concluída: libera o grupo" .-> E
    N --> F["Noel encerra e acorda todo mundo"]
    F --> G["main faz join de todas as threads"]
    G --> H["Calcula métricas, grava CSVs e imprime o resumo"]
```

## O laço do Noel

Um laço infinito (`for (;;)`) que, a cada volta, olha o estado e escolhe **uma** coisa: sair, dormir ou trabalhar. Depois de qualquer trabalho ele volta ao topo e reavalia tudo de novo.

```mermaid
flowchart TD
    S(["Início do laço"]) --> Q1{"Viagem feita E<br/>todos os grupos atendidos?"}
    Q1 -- sim --> FIM(["Sai do laço e encerra"])
    Q1 -- não --> Q2{"Há trabalho pronto?<br/>9 renas ou um grupo de 3"}
    Q2 -- não --> W["Dorme esperando um aviso"]
    W --> Q3{"Passou do tempo limite?"}
    Q3 -- sim --> AB["Marca abortar"] --> FIM
    Q3 -- não --> S
    Q2 -- sim --> Q4{"As 9 renas estão prontas?"}
    Q4 -- "sim (prioridade)" --> V["Prepara a viagem"]
    V --> VR["Libera as renas"] --> S
    Q4 -- não --> G["Atende o próximo grupo de 3 elfos"]
    G --> GR["Libera os 3 elfos"] --> S
```

Pontos da lógica:

- **Renas primeiro**: se as duas demandas estão prontas na mesma volta, a viagem ganha. A versão `--ingenua` inverte isso, para mostrar a violação.
- Ao acordar, Noel **não confia no aviso**: volta ao topo e confere de novo. Por isso um aviso extra ou falso não causa erro.
- Uma ajuda ou preparação nunca é interrompida: só depois de terminar ele volta ao topo e pode escolher as renas.
- O laço termina quando as **duas** demandas acabaram, ou pelo **timeout** de segurança.

## O laço de espera de cada elfo

O elfo não repete trabalho: chega uma vez, entra no grupo aberto e fica num laço de espera até o grupo dele ser atendido.

```mermaid
flowchart TD
    A["Espera a largada"] --> B["Simula a chegada"]
    B --> C["Entra no grupo aberto"]
    C --> D{"Sou o 3º do grupo?"}
    D -- sim --> E["Fecha o grupo, abre o próximo<br/>e acorda Noel"] --> W
    D -- não --> W{"Meu grupo já foi<br/>atendido ou abortou?"}
    W -- não --> X["Dorme até Noel avisar"] --> W
    W -- sim --> F(["Termina"])
```

O grupo fecha **no mesmo instante** em que o 3º elfo entra, então o 4º elfo já cai no grupo seguinte: ninguém invade um grupo em atendimento.

## O laço de espera de cada rena

```mermaid
flowchart TD
    A["Espera a largada"] --> B["Simula a chegada"]
    B --> C["Conta mais uma rena pronta"]
    C --> D{"Sou a 9ª?"}
    D -- sim --> E["Acorda Noel"] --> W
    D -- não --> W{"Viagem concluída<br/>ou abortou?"}
    W -- não --> X["Dorme até Noel avisar"] --> W
    W -- sim --> F(["Termina"])
```

## Por que todo laço de espera é um `while`

Todas as esperas seguem o mesmo padrão: **enquanto a condição não for verdadeira, durma**. Ao acordar, a thread testa de novo antes de seguir. Isso cobre dois casos:

- **Acordar sem motivo** (despertar espúrio): o teste falha e ela volta a dormir.
- **Aviso para outro**: Noel acorda todos os elfos com um único aviso, mas só os do grupo concluído saem; os outros voltam a dormir.

A barreira de largada da `main` usa o mesmo padrão: a `main` dorme enquanto nem todas as threads estão prontas, e cada thread dorme enquanto a largada não foi dada.
